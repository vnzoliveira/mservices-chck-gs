import aio_pika
import asyncpg
import json
from jinja2 import Template
import pdfkit
import boto3
from datetime import datetime
import os
import asyncio
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def get_diploma_data(conn, diploma_id):
    query = """
        SELECT
            d.id,
            d.data_conclusao,
            d.curso,
            d.carga_horaria,
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
        JOIN assinaturas s ON fk_assinatura = s.id
        WHERE d.id = $1
    """
    return await conn.fetchrow(query, diploma_id)

async def process_diploma(message):
    try:    
        data = json.loads(message.body.decode())
        diploma_id = data['diploma_id']
        
        logger.info(f"Processando diploma... ID: {diploma_id}")
        
        conn = await asyncpg.connect('postgres://postgres:postgres@postgres:5432/diplomas_db')
        
        try:
            
            await conn.execute("UPDATE diplomas set status = 'processing' WHERE id = $1", diploma_id)
            
            diploma_data = await get_diploma_data(conn, diploma_id)
            if not diploma_data:
                logger.error(f"Diploma {diploma_id} não encontrado. ")
                return
            
            template_data = dict(diploma_data)
            
            template_data['data_conclusao'] = template_data['data_conclusao'].strftime('%d/%m/%Y')
            template_data['data_nascimento'] = template_data['data_nascimento'].strftime('%d/%m/%Y')
            template_data['data_emissao'] = template_data['data_emissao'].strftime('%d/%m/%Y')
            
            with open('diploma_template.html', 'r', encoding='utf-8') as file:
                template = Template(file.read())
                
            html = template.render(**template_data)
            
            pdf = {
                'page-size' : 'A4',
                'orientation' : 'Landscape',
                'margin-top' : '0',
                'margin-right': '0',
                'margin-bottom': '0',
                'margin-left': '0',
                'encoding': 'UTF-8',
                'no-outline' : None
            }
            
            path = f"/tmp/diploma_{diploma_id}.pdf"
            pdfkit.from_string(html, path, options=pdf)
            
            s3 = boto3.client('s3',
                endpoint_url = f"http://{os.environ['MINIO_URL']}",
                aws_access_key_id = os.environ['MINIO_ACCESS_KEY'],
                aws_secret_access_key=os.environ['MINIO_SECRET_KEY'],
                region_name='us-east-1',
                config=boto3.session.Config(signature_version='s3v4')
            )
            
            bucket = 'diplomas'
            file = f"diploma_{diploma_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
            
            try:
                s3.create_bucket(Bucket=bucket)
            except Exception as e:
                logger.warning(f"Tentativa de criar o bucket falhou: {e}")
            
            s3.upload_file(path,bucket,file)
            url = f"diplomas/{file}"
            
            await conn.execute(
                """
                UPDATE diplomas
                SET pdf_url = $1, status = 'completed'
                WHERE id = $2
                """,
                url,
                diploma_id
            )
            
            os.remove(path)
            logger.info(f"Diploma processado com sucesso! ID: {diploma_id}")
        except Exception as e:
            logger.error(f"Erro processando diploma... ID: {diploma_id}: {str(e)}") 
            await conn.execute("UPDATE diplomas SET status = 'failed' WHERE id = $1", diploma_id)
            raise
        finally:
            await conn.close()
    except Exception as e:
        logger.error(f"Erro na funcao process_diploma: {str(e)}")
        raise

async def main():
    while True:
        try:        
            connection = await aio_pika.connect_robust(os.environ['RABBITMQ_URL'])
            async with connection:    
                canal = await connection.channel()
                fila = await canal.declare_queue("diploma_generation")
            
            async with fila.iterator() as fila_iterator:
                logger.info("Worker iniciado. Aguardando mensagens.")
                
                async for message in fila_iterator:
                    async with message.process():
                        await process_diploma(message)
        except Exception as e:
            logger.error(f"Erro de conexao: {str(e)}")
            await asyncio.sleep(5)

if __name__ == "__main__":
    asyncio.run(main())