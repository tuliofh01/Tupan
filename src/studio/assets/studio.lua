-- ============================================================================
--  TUPAN STUDIO — DSL declarativa (estilo JSON)
--  ---------------------------------------------------------------------------
--  Toda a interface e a cena 3D vivem aqui. O host C++ lê esta tabela via API
--  Lua: não é preciso recompilar para mudar menus, painéis ou objetos.
--  Convenção: { chave = valor, ... } e listas com índices 1..n, como JSON.
-- ============================================================================
return {
    title   = "Tupan Studio",
    version = "0.1.0",

    theme = {
        accent = { 0.25, 0.72, 1.00 },
        panel  = { 0.09, 0.14, 0.22 },
        text   = { 0.91, 0.93, 0.97 }
    },

    menu = {
        {
            label = "Arquivo",
            items = {
                { label = "Recarregar DSL", action = "reload" },
                { label = "Sair",           action = "quit"   }
            }
        },
        {
            label = "Cena",
            items = {
                { label = "Resetar câmera",  action = "reset_camera" },
                { label = "Alternar rotação", action = "toggle_spin"  },
                { label = "Blueprint",        action = "toggle_blueprint" }
            }
        },
        {
            label = "Modo",
            items = {
                { label = "Noite (sorção)",     action = "mode_night" },
                { label = "Dia (regeneração)",  action = "mode_day"   }
            }
        }
    },

    panels = {
        {
            id = "simulacao",
            title = "Simulação",
            controls = {
                { type = "slider", id = "ur",    label = "UR noturna (%)",  min = 20, max = 95, value = 68 },
                { type = "slider", id = "temp",  label = "Temperatura (C)", min = 10, max = 40, value = 24 },
                { type = "slider", id = "noite", label = "Horas de noite",  min = 2,  max = 12, value = 8  },
                { type = "slider", id = "dia",   label = "Horas de dia",    min = 2,  max = 12, value = 6  },
                { type = "button", id = "rodar", label = "Rodar ciclo" }
            }
        },
        {
            id = "resultado",
            title = "Resultado",
            controls = {
                { type = "text", id = "sorvido",  label = "Sorvido (kg)"    },
                { type = "text", id = "potavel",  label = "Potável (L)"     },
                { type = "text", id = "energia",  label = "Energia (kWh)"   },
                { type = "text", id = "custo",    label = "Custo (R$/L)"    },
                { type = "text", id = "status",   label = "Bacia"           }
            }
        }
    },

    camera = {
        target   = { 0.0, 0.7, 0.0 },
        distance = 7.5,
        yaw      = 35.0,
        pitch    = 22.0
    },

    scene = {
        grid = { size = 12.0, step = 1.0, color = { 0.15, 0.20, 0.28 } },
        objects = {
            { id = "ventoinha", shape = "fan",      pos = { -2.8, 1.0, 0.0 }, size = { 0.9, 0.9, 0.2 }, color = { 0.49, 0.42, 1.00 } },
            { id = "leito",     shape = "box",      pos = { -1.3, 0.45, 0.0 }, size = { 1.7, 0.9, 1.7 }, color = { 0.18, 0.62, 0.35 } },
            { id = "vidraria",  shape = "sphere",   pos = {  0.8, 0.95, 0.0 }, size = { 1.0, 1.0, 1.0 }, color = { 0.25, 0.72, 1.00 } },
            { id = "solenoide", shape = "coil",     pos = { -0.1, 0.20, 0.9 }, size = { 1.6, 0.5, 0.5 }, color = { 0.72, 0.23, 0.12 } },
            { id = "filtro",    shape = "cylinder", pos = {  2.0, 0.45, 0.0 }, size = { 0.5, 0.8, 0.5 }, color = { 0.44, 0.88, 0.78 } },
            { id = "bacia",     shape = "box",      pos = {  3.0, 0.35, 0.0 }, size = { 1.1, 0.6, 1.3 }, color = { 0.20, 0.50, 0.90 } }
        }
    }
}
