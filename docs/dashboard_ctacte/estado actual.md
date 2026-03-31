17/3/26
Ya tengo listo para pasar a producción el dashboard.
Ya esta todo commiteado y pushueado en github.
Me falta tomar la decision si usar pc en red para el despliegue o usar un servidor web.

30/3/26
Proximas mejoras:
Status: pendiente
    - En "Por entidad" colocar el control de carga. O sea sacar 3 pestañas y poner dos ya que no es necesario 3. Cuando entro a una entidad me gustaria ver que me falta cargar.
    - En pagina inicio me gustaria mostrar datos generales distribuidos, ver % de cobranza por entidad en un grafico de torta u otro. 

20/3/26
Proximas mejoras:
Status: pendiente
    - Para reflejar mejor la realidad debemos restar a las cobranzas de Lavalle y Lujan las devoluciones realizadas por periodo. Tambien de Tupungato debemos restar las devoluciones de CS
    - Debemos incluir los gastos de procesamiento en los graficos de "inicio"
     -Debemos incluir los gastos de procesamiento en los controles para que genere alerta el no registro. Las entidades que no tienen gastos de procesamiento debemos excluirlas para que no generen alertas la falta de registro, esto se encuentra en config.py
     - Revisar particularidades de algunas entidades para ver que mas considerar
    
    

18/3/26
Proximas mejoras:
Status: realizadas todas
    -La pagina inicio muestra datos redundantes por entidad, en dicha pagina debemos mostrar datos generales de cobranza, % de evolucion mensual, total comisiones por periodo, cobranza por periodo o fecha.
    -Agregar a pagina "por entidad" que muestre el % de evolucion entre cobranzas mensuales.
    -Los graficos de saldo no estan bien, se toma el dato del campo "saldo" de la ctactetrabajo. Es mejor hacer el calculo sumando debe + haber + saldo anterior. Ademas se sacan los graficos de saldo de la pagina inicio ya que tienen sentido por entidad.

