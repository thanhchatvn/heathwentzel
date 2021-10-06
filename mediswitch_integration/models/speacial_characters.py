from odoo import fields, models, api, _
import xml.etree.ElementTree as ET
import time
import json
import requests
import re

import requests
from requests.exceptions import Timeout

from odoo.exceptions import UserError, ValidationError, Warning

class SpeacialCharacter(models.Model):
    _name="speacial.charcters"
    _description = "Special Character to remove from the payload"

    name = fields.Char(string="Character Name", required=True)
    c_code = fields.Char(string="Character Code", required=True)
    c_value = fields.Char(string="Character Value", required=True)

    def speacial_char_escape(self,str1):
        for id in self.search([]):
            str1 = re.sub(str(id.c_code), str(id.c_value), str1)
        return str1

    def echo_operation_scheduler(self):
        company_rec = self.env['res.company'].search([]).filtered(lambda cmp_rec: cmp_rec.production_url and cmp_rec.production_url2)
        self.echo_operation(company_rec[0].id)

    def echo_operation(self,company_id):
        company_id = self.env['res.company'].search([('id','=',int(company_id))])
        url = company_id.production_url
        url2 = company_id.production_url2
        # if url and not url2:
        #     xml1 = """<soapenv:Envelope xmlns:soapenv="http://schemas.xmlsoap.org/soap/envelope/" xmlns:v2="http://gateway.switchonline.co.za/MediswitchGateway/v2">
        #                <soapenv:Header/>
        #                <soapenv:Body>
        #                   <v2:echoOperation/>
        #                </soapenv:Body>
        #             </soapenv:Envelope>"""
        #     try:
        #         headers = {'Content-Type': 'text/xml', 'charset': 'utf-8'}
        #         try:
        #             response = requests.post(url, headers=headers, data=xml1.encode('utf-8'), timeout=20)
        #         except:
        #             flag = True
        #         response_string = ET.fromstring(response.content)
        #     except Exception as e:
        #         raise Warning(_('email Humint Support for assistance. support@humint.co.za or log a ticket at http://www.huminnt-2/submit'  + "\n(Switch System Error)"))
        #
        #     for node in response_string.iter():
        #         if node.tag == 'response':
        #             if str(node.text) == "Mediswitch Gateway OK":
        #                 return url
        #             else:
        #                 raise Warning(_('email Humint Support for assistance. support@humint.co.za or log a ticket at http://www.huminnt-2/submit' + "\n(Switch System Error)"))

        # if url2 and not url:
        #     xml1 = """<soapenv:Envelope xmlns:soapenv="http://schemas.xmlsoap.org/soap/envelope/" xmlns:v2="http://gateway.switchonline.co.za/MediswitchGateway/v2">
        #                            <soapenv:Header/>
        #                            <soapenv:Body>
        #                               <v2:echoOperation/>
        #                            </soapenv:Body>
        #                         </soapenv:Envelope>"""
        #     try:
        #         headers = {'Content-Type': 'text/xml', 'charset': 'utf-8'}
        #         response = requests.post(url2, headers=headers, data=xml1.encode('utf-8'))
        #         response_string = ET.fromstring(response.content)
        #     except Exception as e:
        #         raise Warning(_('email Humint Support for assistance. support@humint.co.za or log a ticket at http://www.humint.co.za/helpdesk/humint-2/submit' + "\n(Switch System Error)"))
        #     for node in response_string.iter():
        #         if node.tag == 'response':
        #             if str(node.text) == "Mediswitch Gateway OK":
        #                 return url2
        #             else:
        #                 raise Warning(_('email Humint Support for assistance. support@humint.co.za or log a ticket at http://www.huminnt-2/submit' + "\n(Switch System Error)"))

        if url and url2:
            flag = False
            if url:
                xml1 = """<soapenv:Envelope xmlns:soapenv="http://schemas.xmlsoap.org/soap/envelope/" xmlns:v2="http://gateway.switchonline.co.za/MediswitchGateway/v2">
                                       <soapenv:Header/>
                                       <soapenv:Body>
                                          <v2:echoOperation/>
                                       </soapenv:Body>
                                    </soapenv:Envelope>"""
                try:
                    headers = {'Content-Type': 'text/xml', 'charset': 'utf-8'}
                    try:
                        response = requests.post(url, headers=headers, data=xml1.encode('utf-8'), timeout=20)
                    except:
                        flag = True
                    response_string = ET.fromstring(response.content)
                except Exception as e:
                    flag = True
                if not flag:
                    for node in response_string.iter():
                        if node.tag == 'response':
                            if str(node.text) == "Mediswitch Gateway OK":
                                cmp_record = self.env['res.company'].search([])
                                cmp_record.write({'select_url': 'production_url'})
                            else:
                                flag = True

            if flag and url2:
                xml1 = """<soapenv:Envelope xmlns:soapenv="http://schemas.xmlsoap.org/soap/envelope/" xmlns:v2="http://gateway.switchonline.co.za/MediswitchGateway/v2">
                                                   <soapenv:Header/>
                                                   <soapenv:Body>
                                                      <v2:echoOperation/>
                                                   </soapenv:Body>
                                                </soapenv:Envelope>"""
                try:
                    headers = {'Content-Type': 'text/xml', 'charset': 'utf-8'}
                    try:
                        response = requests.post(url2, headers=headers, data=xml1.encode('utf-8'), timeout=20)
                    except:
                        cmp_record = self.env['res.company'].search([])
                        cmp_record.write({'select_url': 'error'})
                    response_string = ET.fromstring(response.content)
                except Exception as e:
                    cmp_record = self.env['res.company'].search([])
                    cmp_record.write({'select_url': 'error'})
                    # raise Warning(_(
                    #     'email Humint Support for assistance. support@humint.co.za or log a ticket at http://www.humint.co.za/helpdesk/humint-2/submit' + "\n(Switch System Error)"))
                if response_string:
                    for node in response_string.iter():
                        if node.tag == 'response':
                            if str(node.text) == "Mediswitch Gateway OK":
                                cmp_record = self.env['res.company'].search([])
                                cmp_record.write({'select_url': 'fail_over_url'})
                            else:
                                raise Warning(
                                    _('email Humint Support for assistance. support@humint.co.za or log a ticket at http://www.huminnt-2/submit' + "\n(Switch System Error)"))
