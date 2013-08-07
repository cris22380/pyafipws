#!/usr/bin/python
# -*- coding: utf8 -*-
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by the
# Free Software Foundation; either version 3, or (at your option) any later
# version.
#
# This program is distributed in the hope that it will be useful, but
# WITHOUT ANY WARRANTY; without even the implied warranty of MERCHANTIBILITY
# or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU General Public License
# for more details.

"Pruebas Liquidación Primaria Electrónica de Granos web service WSLPG (AFIP)"

__author__ = "Mariano Reingart <reingart@gmail.com>"
__copyright__ = "Copyright (C) 2013 Mariano Reingart"
__license__ = "GPL 3.0"


import unittest
import sys
from decimal import Decimal

sys.path.append("/home/reingart")        # TODO: proper packaging

from pyafipws import utils
from pyafipws.wsaa import WSAA
from pyafipws.wslpg import WSLPG

import pysimplesoap.client
print pysimplesoap.client.__version__
#assert pysimplesoap.client.__version__ >= "1.08c"


WSDL = "https://fwshomo.afip.gov.ar/wslpg/LpgService?wsdl"
CUIT = 20267565393
CERT = "/home/reingart/pyafipws/reingart.crt"
PRIVATEKEY = "/home/reingart/pyafipws/reingart.key"
CACERT = "/home/reingart/pyafipws/afip_root_desa_ca.crt"
CACHE = "/home/reingart/pyafipws/cache"

# Autenticación:
wsaa = WSAA()
tra = wsaa.CreateTRA(service="wslpg")
cms = wsaa.SignTRA(tra, CERT, PRIVATEKEY)
wsaa.Conectar()
wsaa.LoginCMS(cms)

class TestIssues(unittest.TestCase):
    
    def setUp(self):
        sys.argv.append("--trace")                  # TODO: use logging
        self.wslpg = wslpg = WSLPG()
        wslpg.LanzarExcepciones = True
        wslpg.Conectar(url=WSDL, cacert=None, cache=CACHE)
        wslpg.Cuit = CUIT
        wslpg.Token = wsaa.Token
        wslpg.Sign = wsaa.Sign                    
                    
    def test_liquidacion(self):
        "Prueba de autorización (obtener COE) liquidación electrónica de granos"
        wslpg = self.wslpg
        pto_emision = 99
        ok = wslpg.ConsultarUltNroOrden(pto_emision)
        self.assertTrue(ok)
        ok = wslpg.CrearLiquidacion(
                pto_emision=pto_emision,
                nro_orden=wslpg.NroOrden + 1, 
                cuit_comprador=wslpg.Cuit,
                nro_act_comprador=29, nro_ing_bruto_comprador=wslpg.Cuit,
                cod_tipo_operacion=1,
                es_liquidacion_propia='N', es_canje='N',
                cod_puerto=14, des_puerto_localidad="DETALLE PUERTO",
                cod_grano=31, 
                cuit_vendedor=23000000019, nro_ing_bruto_vendedor=23000000019,
                actua_corredor="N", liquida_corredor="N", 
                cuit_corredor=0,
                comision_corredor=0, nro_ing_bruto_corredor=0,
                fecha_precio_operacion="2013-02-07",
                precio_ref_tn=2000,
                cod_grado_ref="G1",
                cod_grado_ent="FG",
                factor_ent=98, val_grado_ent=1.02,
                precio_flete_tn=10,
                cont_proteico=20,
                alic_iva_operacion=10.5,
                campania_ppal=1213,
                cod_localidad_procedencia=5544,
                cod_prov_procedencia=12,
                datos_adicionales="DATOS ADICIONALES",
                peso_neto_sin_certificado=10000,
                cod_prov_procedencia_sin_certificado=1,
                cod_localidad_procedencia_sin_certificado=15124,
                )        

        wslpg.AgregarRetencion(
                        codigo_concepto="RI",
                        detalle_aclaratorio="DETALLE DE IVA",
                        base_calculo=1000,
                        alicuota=10.5,
                    )
        wslpg.AgregarRetencion(                        
                        codigo_concepto="RG",
                        detalle_aclaratorio="DETALLE DE GANANCIAS",
                        base_calculo=100,
                        alicuota=15,
                    )
        ok = wslpg.AutorizarLiquidacion()
        self.assertTrue(ok)
        self.assertIsInstance(wslpg.COE, basestring)
        self.assertEqual(len(wslpg.COE), len("330100013142")) 

    def test_anular(self):
        "Prueba de anulación de una liquidación electrónica de granos"
        wslpg = self.wslpg
        self.test_liquidacion()                     # autorizo una nueva liq.
        ok = wslpg.AnularLiquidacion(wslpg.COE)     # la anulo
        self.assertTrue(ok)
        self.assertEqual(wslpg.Resultado, "A")

    def test_ajuste_unificado(self):
        "Prueba de ajuste unificado de una liquidación de granos (WSLPGv1.4)"
        wslpg = self.wslpg
        # solicito una liquidación para tener el COE autorizado a ajustar:
        self.test_liquidacion()
        coe = wslpg.COE
        # solicito el último nro de orden para la nueva liquidación de ajuste:
        pto_emision = 55
        ok = wslpg.ConsultarUltNroOrden(pto_emision)
        self.assertTrue(ok)
        nro_orden = wslpg.NroOrden + 1
        # creo el ajuste base y agrego los datos de certificado:
        wslpg.CrearAjusteBase(pto_emision=pto_emision, 
                              nro_orden=nro_orden, 
                              coe_ajustado=coe)
        wslpg.AgregarCertificado(tipo_certificado_deposito=5,
                       nro_certificado_deposito=555501200729,
                       peso_neto=10000,
                       cod_localidad_procedencia=3,
                       cod_prov_procedencia=1,
                       campania=1213,
                       fecha_cierre='2013-04-15')
        # creo el ajuste de crédito (ver documentación AFIP)
        wslpg.CrearAjusteCredito(
                diferencia_peso_neto=1000, diferencia_precio_operacion=100,
                cod_grado="G2", val_grado=1.0, factor=100,
                diferencia_precio_flete_tn=10,
                datos_adicionales='AJUSTE CRED UNIF',
                concepto_importe_iva_0='Alicuota Cero',
                importe_ajustar_Iva_0=900,
                concepto_importe_iva_105='Alicuota Diez',
                importe_ajustar_Iva_105=800,
                concepto_importe_iva_21='Alicuota Veintiuno',
                importe_ajustar_Iva_21=700,
            )
        wslpg.AgregarDeduccion(codigo_concepto="AL",
                               detalle_aclaratorio="Deduc Alm",
                               dias_almacenaje="1",
                               precio_pkg_diario=0.01,
                               comision_gastos_adm=1.0,
                               base_calculo=1000.0,
                               alicuota=10.5, )
        wslpg.AgregarRetencion(codigo_concepto="RI",
                               detalle_aclaratorio="Ret IVA",
                               base_calculo=1000,
                               alicuota=10.5, )
        # creo el ajuste de débito (ver documentación AFIP)
        wslpg.CrearAjusteDebito(
                diferencia_peso_neto=500, diferencia_precio_operacion=100,
                cod_grado="G2", val_grado=1.0, factor=100,
                diferencia_precio_flete_tn=0.01,
                datos_adicionales='AJUSTE DEB UNIF',
                concepto_importe_iva_0='Alic 0',
                importe_ajustar_Iva_0=250,
                concepto_importe_iva_105='Alic 10.5',
                importe_ajustar_Iva_105=200,
                concepto_importe_iva_21='Alicuota 21',
                importe_ajustar_Iva_21=50,
            )
        wslpg.AgregarDeduccion(codigo_concepto="AL",
                               detalle_aclaratorio="Deduc Alm",
                               dias_almacenaje="1",
                               precio_pkg_diario=0.01,
                               comision_gastos_adm=1.0,
                               base_calculo=500.0,
                               alicuota=10.5, )
        wslpg.AgregarRetencion(codigo_concepto="RI",
                               detalle_aclaratorio="Ret IVA",
                               base_calculo=100,
                               alicuota=10.5, )
        # autorizo el ajuste:
        ok = wslpg.AjustarLiquidacionUnificado()
        self.assertTrue(ok)
        # verificar respuesta general:
        self.assertIsInstance(wslpg.COE, basestring)
        self.assertEqual(len(wslpg.COE), len("330100013133"))
        self.assertEqual(wslpg.Estado, "AC")
        self.assertEqual(wslpg.SubtotalGeneral, Decimal("-734.10"))
        self.assertEqual(wslpg.TotalIva105, Decimal("0"))
        self.assertEqual(wslpg.TotalIva21, Decimal("0"))
        self.assertEqual(wslpg.TotalRetencionesGanancias, Decimal("0"))
        self.assertEqual(wslpg.TotalRetencionesIVA, Decimal("-94.50"))
        self.assertEqual(wslpg.TotalNetoAPagar, Decimal("-639.07"))
        self.assertEqual(wslpg.TotalIvaRg2300_07, Decimal("94.50"))
        self.assertEqual(wslpg.TotalPagoSegunCondicion, Decimal("-733.57"))
        # verificar ajuste credito
        ok = wslpg.AnalizarAjusteCredito()
        self.assertTrue(ok)
        self.assertEqual(wslpg.GetParametro("precio_operacion"), "1.900")
        self.assertEqual(wslpg.GetParametro("total_peso_neto"), "1000")
        self.assertEqual(wslpg.TotalDeduccion, Decimal("11.05"))
        self.assertEqual(wslpg.TotalPagoSegunCondicion, Decimal("2780.95"))
        self.assertEqual(wslpg.GetParametro("importe_iva"), "293.16")
        self.assertEqual(wslpg.GetParametro("operacion_con_iva"), "3085.16")
        self.assertEqual(wslpg.GetParametro("deducciones", 0, "importe_iva"), "1.05")
        # verificar ajuste debito
        ok = wslpg.AnalizarAjusteDebito()
        self.assertTrue(ok)
        self.assertEqual(wslpg.GetParametro("precio_operacion"), "2.090")
        self.assertEqual(wslpg.GetParametro("total_peso_neto"), "500")
        self.assertEqual(wslpg.TotalDeduccion, Decimal("11.05"))
        self.assertEqual(wslpg.TotalPagoSegunCondicion, Decimal("2047.38"))
        self.assertEqual(wslpg.GetParametro("importe_iva"), "215.55")
        self.assertEqual(wslpg.GetParametro("operacion_con_iva"), "2268.45")
        self.assertEqual(wslpg.GetParametro("retenciones", 0, "importe_retencion"), "10.50")
        
    def test_ajuste_contrato(self):
        wslpg = self.wslpg
        wslpg.CrearAjusteBase(pto_emision=55, nro_orden=1, 
                              nro_contrato=100001005,
                              nro_act_comprador=41, 
                              cod_grano=41,
                              cuit_vendedor=30000000007,
                              cuit_comprador=99999999999,
                              precio_ref_tn=100,
                              cod_grado_ent="G1",
                              val_grado_ent=1.01,
                              precio_flete_tn=1000,
                              cod_puerto=14,
                              des_puerto_localidad="Desc Puerto",
                              )
        wslpg.CrearAjusteCredito(
                concepto_importe_iva_0='Ajuste IVA al 0%',
                importe_ajustar_Iva_0=100,
            )
        wslpg.CrearAjusteDebito(
                concepto_importe_iva_105='Ajuste IVA al 10.5%',
                importe_ajustar_Iva_105=100,
            )
        wslpg.AgregarDeduccion(codigo_concepto="OD",
                               detalle_aclaratorio="Otras Deduc",
                               dias_almacenaje="1",
                               base_calculo=100.0,
                               alicuota=10.5, )

        ret = wslpg.AjustarLiquidacionContrato()

    def test_ajuste_papel(self):
        wslpg = self.wslpg
        wslpg.CrearAjusteBase(pto_emision=50,
                              nro_orden=1,
                              tipo_formulario=6,
                              nro_formulario="000101800999",
                              actividad=46,
                              cuit_comprador=99999999999,
                              nro_ing_bruto_comprador=99999999999,
                              tipo_operacion=1,
                              cod_grano=31,
                              cuit_vendedor=30000000007,
                              nro_ing_bruto_vendedor=30000000007,
                              cod_provincia=1,
                              cod_localidad=5)
        wslpg.AgregarCertificado(tipo_certificado_deposito=5,
                       nro_certificado_deposito=555501200802,
                       peso_neto=10000,
                       cod_localidad_procedencia=5,
                       cod_prov_procedencia=1,
                       campania=1213,
                       fecha_cierre='2013-07-12')
        wslpg.CrearAjusteCredito(
                concepto_importe_iva_21='IVA al 21%',
                importe_ajustar_Iva_21=1500,
            )
        wslpg.AgregarRetencion(codigo_concepto="RI",
                               detalle_aclaratorio="Ret IVA",
                               base_calculo=1500,
                               alicuota=8, )
        wslpg.CrearAjusteDebito(
                concepto_importe_iva_105='IVA al 0%',
                importe_ajustar_Iva_105=100,
            )

        ret = wslpg.AjustarLiquidacionUnificadoPapel()
        

if __name__ == '__main__':
    unittest.main()

