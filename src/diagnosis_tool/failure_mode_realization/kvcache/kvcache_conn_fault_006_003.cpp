#include "kvcache_conn_fault_006_003.h"

#include "../../failure_mode_factory.h"

namespace diag {

static AutoRegister<KvcacheConnFault006_003> g_kvcacheconnfault("kvcache_conn_fault_006_003");

bool KvcacheConnFault006_003::IsValid(const std::vector<std::string> &fields)
{
    if (fields.size() <= 7) {
        return false;
    }
    const std::string &message = fields[7];
    return ((message.find("urma") != std::string::npos && message.find("payload") != std::string::npos) ||
            message.find("Failed to urma") != std::string::npos);
}

std::string KvcacheConnFault006_003::GetName() const
{
    return "code=5 + urma ... payload ... (URMA)。";
}

std::string KvcacheConnFault006_003::GetRootCauseDesc() const
{
    return "URMA数据面payload问题，属于URMA责任（08手册:L194）。";
}

RootCause KvcacheConnFault006_003::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string KvcacheConnFault006_003::GetFixSuggDesc() const
{
    return "向下级匹配URMA故障（见kvcache_conn_fault_028节）（08手册:L281-308）。";
}

std::string KvcacheConnFault006_003::GetValidationMethodDesc() const
{
    return "通过日志关键字识别（08手册:L194）：匹配urma.*payload或Failed "
           "to urma。";
}

std::string KvcacheConnFault006_003::GetId() const
{
    return "kvcache_conn_fault_006_003";
}
} // namespace diag
