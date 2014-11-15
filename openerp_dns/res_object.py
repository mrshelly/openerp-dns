# -*- coding: utf-8 -*-

import httplib, urllib
import socket,time
import json
import logging
socket.setdefaulttimeout(3)

from openerp.osv import fields, osv
from openerp.tools.translate import _

os_encode = 'utf-8'
import os
if os.name == 'nt':
    os_encode='gbk'

_logger = logging.getLogger(__name__)

socket_trytimes = [0.1, 2]

class res_network_domain(osv.osv):
    _name = "res.network.domain"
    _description = "Domain"

    _columns = {
        'name': fields.char('Name', size=64, required=True, help="The domain."),
        'isp': fields.selection([
            ('dnspod', 'DNSpod'),
            ], 'Domain ISP', required=True),
        'api_user': fields.char('API User', size=64, required=True),
        'api_pass': fields.char('API Pass', size=64, required=True),
        'api_token': fields.char('API Token', size=128),
        'api_args': fields.text('API Parameters'),
        'active': fields.boolean('Active'),
    }
    _defaults = {
        'isp': 'dnspod',
        'active': True,
    }

    def _check_ip(self, cr, uid, ids, context=None):
        sock = socket.create_connection(('ns1.dnspod.net', 6666))
        ip = False
        for try_ts in socket_trytimes:
            try:
                ip = sock.recv(16)
                sock.close()
                break
            except:
                time.sleep(try_ts)
        del sock
        return ip

    def act_sync_all(self, cr, uid, ids, context=None):
        ids = self.search(cr, uid, [('active', '=', True)], context=context)
        ret = self.sync_ip(cr, uid, ids, context=context)
        return ret

    def sync_ip(self, cr, uid, ids, context=None):
        context = context or {}
        ids = isinstance(ids, (int,long)) and [ids] or ids

        ip = self._check_ip(cr, uid, [], context=context)
        if ip and ids[0]:
            res = self.browse(cr, uid, ids[0], context=context)
            if res.isp == 'dnspod':
                # login_email=api@dnspod.com&login_password=password&format=json&domain_id=2317346&record_id=16894439&value=3.2.2.2&record_type=A&record_line=默认
                params = json.loads(res.api_args)
                params.update({'record_line': params['record_line'].encode('utf-8')})
                params.update({'record_id': int(params['record_id'])})
                params.update({
                    'login_email': res.api_user,
                    'login_password': res.api_pass,
                    'format': 'json',
                    'lang': 'cn',
                    'error_on_empty': 'no',
                })
                params.update(dict(value=ip))

                conn = httplib.HTTPSConnection('dnsapi.cn')
                ret = False
                for try_ts in socket_trytimes:
                    try:
                        headers = {"Content-type": "application/x-www-form-urlencoded", "Accept": "text/json"}
                        conn.request("POST", "/Record.Modify", urllib.urlencode(params), headers)

                        response = conn.getresponse()
                        response_str = response.read()
                        ret = json.loads(response_str)
                        if not (ret.get("status", {}).get("code") == "1"):
                            raise Exception(ret)
                        conn.close()
                        break
                    except:
                        time.sleep(try_ts)
                del conn
                return True
        else:
            raise
        return True

    def act_config(self, cr, uid, ids, context=None):
        context = context or {}
        ids = isinstance(ids, (int,long)) and [ids] or ids
        if not ids[0]:
            raise
        res = self.browse(cr, uid, ids[0], context=context)
        context.update({'domain_id': res.id})
        ret ={
            'name': _('Domain Config Wizard'),
            'type': 'ir.actions.act_window',
            'context': context,
            'res_model': 'wizard.config.dnspod.api',
            'view_type': 'form',
            'view_mode': 'form',
            'target': 'new',
        }
        return ret

class wizard_config_dnspod_api(osv.osv_memory):
    _name = "wizard.config.dnspod.api"
    _description = "DNSPod Domain Configration"
    _base_url = 'dnsapi.cn'
    _headers = {"Content-type": "application/x-www-form-urlencoded", "Accept": "text/json"}

    _columns = {
        'sub_domain': fields.char('Sub Domain', required=True),
        'domain_id': fields.many2one('res.network.domain', 'Domain'),
        'record_line': fields.selection([
            (u'默认', u'默认'),
            (u'电信', u'电信'),
            (u'联通', u'联通'),
            (u'教育网', u'教育网'),
            ], 'Record Line', required=True),
    }

    _defaults = {
        'sub_domain': 'www',
        'domain_id': lambda self, cr, uid, context=None: (context is None) and False or context.get('domain_id', False),
        'record_line': u'默认',
    }

    def _get_domain_list(self, cr, uid, ids, context=None):
        context = context or {}
        ids = isinstance(ids, (int,long)) and [ids] or ids
        if not ids[0]:
            raise
        res = self.browse(cr, uid, ids[0], context=context)
        # curl -X POST https://dnsapi.cn/Domain.List -d 'login_email=api@dnspod.com&login_password=password&format=json'
        params = {
            'login_email': res.domain_id.api_user,
            'login_password': res.domain_id.api_pass,
            'format': 'json',
            'lang': 'cn',
            'error_on_empty': 'no',
        }

        _logger.info('[DnsPod] Domain.List')
        conn = httplib.HTTPSConnection(self._base_url)
        ret = False
        for try_ts in socket_trytimes:
            try:
                conn.request("POST", "/Domain.List", urllib.urlencode(params), self._headers)

                response = conn.getresponse()
                ret = json.loads(response.read())
                _logger.info('[DnsPod] Domain.List ret: %s' % json.dumps(ret))
                if not (ret.get("status", {}).get("code") == "1"):
                    _logger.info('[DnsPod] Domain.List Exception: %s' % str(ret))
                    raise Exception(ret)
                conn.close()
                break
            except:
                time.sleep(try_ts)
        del conn
        return ret

    def _get_domain_info(self, cr, uid, ids, domain_id, context=None):
        context = context or {}
        ids = isinstance(ids, (int,long)) and [ids] or ids
        if not ids[0]:
            raise
        res = self.browse(cr, uid, ids[0], context=context)
        # curl -X POST https://dnsapi.cn/Domain.Info  -d 'login_email=api@dnspod.com&login_password=password&format=json&domain_id=2059079'
        params = {
            'login_email': res.domain_id.api_user,
            'login_password': res.domain_id.api_pass,
            'format': 'json',
            'lang': 'cn',
            'error_on_empty': 'no',
            'domain_id': domain_id,
        }

        _logger.info('[DnsPod] Domain.Info')
        conn = httplib.HTTPSConnection(self._base_url)
        ret = False
        for try_ts in socket_trytimes:
            try:
                conn.request("POST", "/Domain.Info", urllib.urlencode(params), self._headers)

                response = conn.getresponse()
                ret = json.loads(response.read())
                _logger.info('[DnsPod] Domain.Info ret: %s' % json.dumps(ret))
                if not (ret.get("status", {}).get("code") == "1"):
                    _logger.info('[DnsPod] Domain.Info Exception: %s' % str(ret))
                    raise Exception(ret)
                conn.close()
                break
            except:
                time.sleep(try_ts)
        del conn
        return ret

    def _get_record_list(self, cr, uid, ids, domain_id, context=None):
        context = context or {}
        ids = isinstance(ids, (int,long)) and [ids] or ids
        if not ids[0]:
            raise
        res = self.browse(cr, uid, ids[0], context=context)
        # curl -X POST https://dnsapi.cn/Record.List -d 'login_email=api@dnspod.com&login_password=password&format=json&domain_id=2317346'
        params = {
            'login_email': res.domain_id.api_user,
            'login_password': res.domain_id.api_pass,
            'format': 'json',
            'lang': 'cn',
            'error_on_empty': 'no',
            'domain_id': domain_id,
        }

        _logger.info('[DnsPod] Record.List')
        conn = httplib.HTTPSConnection(self._base_url)
        ret = False
        for try_ts in socket_trytimes:
            try:
                conn.request("POST", "/Record.List", urllib.urlencode(params), self._headers)

                response = conn.getresponse()
                ret = json.loads(response.read())
                _logger.info('[DnsPod] Record.List ret: %s' % json.dumps(ret))
                if not (ret.get("status", {}).get("code") == "1"):
                    _logger.info('[DnsPod] Record.List Exception: %s' % str(ret))
                    raise Exception(ret)
                conn.close()
                break
            except:
                time.sleep(try_ts)
        del conn
        return ret

    def _set_record_info_A(self, cr, uid, ids, domain_id, record_id, val, record_line='默认', record_type='A', context=None):
        context = context or {}
        ids = isinstance(ids, (int,long)) and [ids] or ids
        if not ids[0]:
            raise
        res = self.browse(cr, uid, ids[0], context=context)
        # curl -X POST https://dnsapi.cn/Record.Modify -d 'login_email=api@dnspod.com&login_password=password&format=json&domain_id=2317346&record_id=16894439&value=3.2.2.2&record_type=A&record_line=默认'
        params = {
            'login_email': res.domain_id.api_user,
            'login_password': res.domain_id.api_pass,
            'format': 'json',
            'lang': 'cn',
            'error_on_empty': 'no',
            'domain_id': domain_id,
            'record_id': record_id,
            'value': val,
            'record_type': record_type,
            'record_line': record_line,
        }

        _logger.info('[DnsPod] Record.Modify')
        conn = httplib.HTTPSConnection(self._base_url)
        ret = False
        for try_ts in socket_trytimes:
            try:
                conn.request("POST", "/Record.List", urllib.urlencode(params), self._headers)

                response = conn.getresponse()
                ret = json.loads(response.read())
                _logger.info('[DnsPod] Record.Modify ret: %s' % json.dumps(ret))
                if not (ret.get("status", {}).get("code") == "1"):
                    _logger.info('[DnsPod] Record.Modify Exception: %s' % str(ret))
                    raise Exception(ret)
                conn.close()
                break
            except:
                time.sleep(try_ts)
        del conn
        return ret

    def act_done(self, cr, uid, ids, context=None):
        context = context or {}
        ids = isinstance(ids, (int,long)) and [ids] or ids
        if not ids[0]:
            raise
        res = self.browse(cr, uid, ids[0], context=context)

        domain_res = self._get_domain_list(cr, uid, ids, context=context)
        domain_id = False
        if not domain_res:
            raise
        for d in domain_res['domains']:
            if d['name'] == res.domain_id.name:
                _logger.info('[DnsPod] Wizard Got domain: %s' % d['name'])
                domain_id = d['id']
        if not domain_id:
            raise

        record_res = self._get_record_list(cr, uid, ids, domain_id, context=context)
        record_id = False
        if not record_res:
            raise
        for r in record_res['records']:
            if res.sub_domain == '%s.%s' % (r['name'], res.domain_id.name):
                _logger.info('[DnsPod] Wizard Got record: %s.%s' % (r['name'], res.domain_id.name))
                record_id = r['id']
        if not record_id:
            raise
        domain_obj = self.pool.get('res.network.domain')
        params = {
            'domain_id': domain_id,
            'record_id': record_id,
            'sub_domain': res.sub_domain.replace('.%s' % res.domain_id.name, ''),
            'ttl': 120,
            'record_type': 'A',
            'record_line': res.record_line,
        }
        ret = domain_obj.write(cr, uid, res.domain_id.id, {'api_args': json.dumps(params)}, context=context)
        return ret

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
