from pathlib import Path
p = Path("source/app.d")
s = p.read_text()
start = s.index("\t// Initializing ADI and machine")
end = s.index("\n\tif (skipServerStartup)", start)
s = s[:start] + s[end:]
start = s.index("\t\timport std.datetime.systime;", s.index("void handleV1Request"))
end = s.index("\n\t}\n", start)
s = s[:start] + '''\t\tres.headers["Implementation-Version"] = brandingCode;
\t\tres.headers["Cache-Control"] = "no-store";
\t\tres.writeBody("{\\"name\\":\\"Zyn Anisette\\",\\"protocol\\":3,\\"status\\":\\"ready\\"}", "application/json");''' + s[end:]
s = s.replace('provisioningPath.buildPath(identifier)', 'provisioningPath.buildPath(randomUUID().toString())')
s = s.replace('log.infoF!(" [<< %s] Correct identifier (%s).")(requestUUID, identifier);', 'log.info("Identifier accepted.");')
s = s.replace('log.infoF!("[<< %s] Correct identifier (%s).")(requestUUID, identifier);', 'log.info("Identifier accepted.");')
p.write_text(s)
