-- ============================================================================
--  TUPAN — script de simulação headless (executado por `tupan_script`)
--  ---------------------------------------------------------------------------
--  Demonstra o binding luaaa: o módulo `tupan.*` é o núcleo C++ exposto ao Lua.
--  Rode:  ./build/tupan_script            (usa este arquivo por padrão)
--         ./build/tupan_script caminho.lua
-- ============================================================================

print(string.format("Tupan %s — varredura de umidade (luaaa)", tupan.version))

local noite, dia, temp = 8, 6, 24
print(string.format("Ciclo padrão: %.0f h noite + %.0f h dia, %.0f C\n", noite, dia, temp))

local urbs = { 40, 50, 60, 68, 75, 85, 95 }
for _, ur in ipairs(urbs) do
    local litros = tupan.potavel(noite, dia, ur, temp)
    local kwh = tupan.energia_kwh(noite, dia, ur, temp)
    local eff = tupan.l_por_kwh(noite, dia, ur, temp)
    print(string.format("  UR %3d%%  ->  %.3f L  |  %.3f kWh  |  %.2f L/kWh", ur, litros, kwh, eff))
end

local sorvido = tupan.sorvido(noite, 68, temp)
print(string.format("\nLeito (UR 68%%): %.3f kg de agua sorvida na noite", sorvido))
