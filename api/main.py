from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from datetime import date
import aioredis
import aio_pika
import aysncpg
import json

app = FastAPI()

class AlunoBase(BaseModel):
    nome : str
    nacionalidade : str
    estado : str
    data_nascimento : date
    documento : str

class AssinaturaBase(BaseModel):
    nome_assinatura : str
    cargo : str

class DiplomaRequest(BaseModel):
    data_conclusao : date
    curso : str
    carga_horaria : int
    aluno : AlunoBase
    assinatura : AssinaturaBase
    
async def get_cache(key : str):
    redis = await aioredis.create_redis_pool('redis://redis:6379')
    try:
        cached_data = await redis.get(key)
        return cached_data
    finally:
        redis.close()
        await redis.wait_closed()

async def set_cache(key : str, value : str, expire : int = 3600):
    redis = await aioredis.create_redis_pool('redis://redis:6379')
    try:
        await redis.set(key, value, expire=expire)
    finally:
        redis.close()
        redis.wait_closed()


@app.post("/diplomas")
async def cria_diploma(diploma : DiplomaRequest):
    conn = await aysncpg.connect('postgresql://postgres:postgres@postgres:5432/diplomas_db')
    try:
        async with conn.transaction():
            aluno = """
            INSERT INTO alunos(nome, nacionalidade, estado, data_nascimento, documento)
            VALUES($1, $2, $3, $4, $5)
            ON CONFLICT (documento) DO UPDATE
            SET nome = EXCLUDED.nome,
            nacionalidade = EXCLUDED.nacionalidade,
            estado = EXCLUDED.estado,
            data_nascimento = EXCLUDED.data_nascimento
            RETURNING id
            """
            aluno_id = await conn.fetchval(
                aluno,
                diploma.aluno.nome,
                diploma.aluno.nacionalidade,
                diploma.aluno.estado,
                diploma.aluno.data_nascimento,
                diploma.aluno.documento
            )
            
            assinatura = """
                INSERT INTO assinaturas (nome_assinatura, cargo)
                VALUES ($1, $2)
                ON CONFLICT (nome_assinatura, cargo) DO UPDATE
                SET nome_assinatura = EXCLUDED.nome_assinatura,
                    cargo = EXCLUDED.cargo
                RETURNING id
            """
            
            assinatura_id = await conn.fetchval(
                assinatura,
                diploma.assinatura.nome_assinatura,
                diploma.assinatura.cargo
            )
            
            diploma_query = """
                INSERT INTO diplomas (
                    data_conclusao, curso, carga_horaria,
                    fk_aluno, fk_assinatura
                ) VALUES ($1, $2, $3, $4, $5)
                RETURNING id
            """
            
            diploma_id = await conn.fetchval(
                diploma_query,
                diploma.data_conclusao,
                diploma.curso,
                diploma.carga_horaria,
                aluno_id,
                assinatura_id
            )
            
            connection = await aio_pika.connect_robust("amqp://admin:admin_password@rabbitmq:5672/")
            canal = await connection.channel()
            fila = await canal.declare_queue("diploma_generation")
            
            message = {
                "diploma_id": diploma_id,
                **diploma.dict()
            }
            
            await canal.default_exchange.publish(
                aio_pika.Message(body=json.dumps(message).encode()),
                routing_key="diploma_generation"
            )
            
            await connection.close()
            
            return {"diploma_id":diploma_id}
    finally:
        await conn.close()

@app.get("/diplomas/{diploma_id}")
async def get_diploma(diploma_id : int):
    cached_data = await get_cache(f"diploma:{diploma_id}")
    if cached_data:
        return json.loads(cached_data)
    
    conn = await asyncpg.connect('postgresql://postgres:postgres@:5432/diplomas_db')
    try:
        query = """
             SELECT 
                d.id,
                d.data_conclusao,
                d.curso,
                d.carga_horaria,
                d.status,
                d.pdf_url,
                d.data_emissao,
                a.nome,
                a.nacionalidade,
                a.estado,
                a.data_nascimento,
                a.documento,
                s.nome_assinatura,
                s.cargo
            FROM diplomas d
            JOIN alunos a ON d.fk_aluno = a.id
            JOIN assinaturas s ON d.fk_assinatura = s.id
            WHERE d.id = $1
        """
        record = await conn.fetchrow(query, diploma_id)
        
        if not record:
            raise HTTPException(status_code = 404, detail="Diploma nao encontrado.")
        
        result = dict(record)
        await set_cache(f"diploma:{diploma_id}", json.dumps(result))
        
        return result
    finally:
        await conn.close()
