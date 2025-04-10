from flask import Blueprint, jsonify, Response, make_response, request
import requests
import logging
from flask_cors import cross_origin

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

bp = Blueprint('proxy', __name__)

@bp.route('/doi/<path:doi>', methods=['GET'])
@cross_origin()
def proxy_doi(doi):
    """
    Proxy DOI requests to Crossref
    """
    try:
        response = requests.get(
            f'https://api.crossref.org/works/{doi}',
            headers={
                'User-Agent': 'YourApp/1.0 (https://yourdomain.com; mailto:support@yourdomain.com)'
            }
        )
        return jsonify(response.json()), response.status_code
    except Exception as e:
        logger.error(f"DOI proxy error: {str(e)}")
        return jsonify({'error': str(e)}), 500

@bp.route('/arxiv/<path:arxiv_id>', methods=['GET'])
@cross_origin()
def proxy_arxiv(arxiv_id):
    """
    Proxy arXiv API requests
    """
    try:
        response = requests.get(f'https://export.arxiv.org/api/query?id_list={arxiv_id}')
        return Response(
            response.content,
            content_type='application/xml',
            status=response.status_code
        )
    except Exception as e:
        logger.error(f"arXiv proxy error: {str(e)}")
        return jsonify({'error': str(e)}), 500

@bp.route('/pubmed/<pmid>', methods=['GET'])
@cross_origin()
def proxy_pubmed(pmid):
    """
    Proxy PubMed API requests
    """
    try:
        response = requests.get(
            f'https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esummary.fcgi?db=pubmed&id={pmid}&retmode=json'
        )
        return jsonify(response.json()), response.status_code
    except Exception as e:
        logger.error(f"PubMed proxy error: {str(e)}")
        return jsonify({'error': str(e)}), 500

@bp.route('/proquest/<id>', methods=['GET'])
@cross_origin()
def proxy_proquest(id):
    """
    Proxy ProQuest document requests
    """
    try:
        response = requests.get(f'https://www.proquest.com/openview/{id}')
        return Response(
            response.content,
            content_type='text/html',
            status=response.status_code
        )
    except Exception as e:
        logger.error(f"ProQuest proxy error: {str(e)}")
        return jsonify({'error': str(e)}), 500

@bp.after_request
def after_request(response):
    """
    Add CORS headers to all responses
    """
    response.headers.add('Access-Control-Allow-Origin', '*')
    response.headers.add('Access-Control-Allow-Headers', 'Content-Type, Authorization')
    response.headers.add('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
    return response 