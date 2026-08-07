#include "kvcache_conn_fault_002_005.h"

#include "../../failure_mode_factory.h"

namespace diag {

static AutoRegister<KvcacheConnFault002_005> g_kvcacheconnfault("kvcache_conn_fault_002_005");

bool KvcacheConnFault002_005::IsValid(const std::vector<std::string> &fields)
{
    // 来源：kvcache_conn_fault_mode.md:L194-217
    // 通过runtime log的message字段匹配K_NOT_FOUND或Can't find object
    // 注意：此故障在runtime log中匹配（access log中code=0配合respMsg含NOT_FOUND同样确认）
    // 但这里按access log字段检查(respMsg=第13列即fields[12])
    if (fields.size() > 12) {
        const std::string &respMsg = fields[12];
        if (respMsg.find("Can't find object") != std::string::npos ||
            respMsg.find("NOT_FOUND") != std::string::npos) {
            return true;
        }
    }
    // runtime log检查：message字段（来源：08手册:L251）
    // 在runtime log场景中fields[7]是message
    if (fields.size() > 7) {
        const std::string &message = fields[7];
        return (message.find("Can't find object") != std::string::npos ||
                message.find("K_NOT_FOUND") != std::string::npos);
    }
    return false;
}

std::string KvcacheConnFault002_005::GetName() const
{
    return "respMsg对象不存在故障。";
}

std::string KvcacheConnFault002_005::GetRootCauseDesc() const
{
    return "对象不存在，属于用户侧问题。可能原因：业务未Put直接Get、"
           "对象已过期（TTL）、key拼写错误（08手册:L251）。";
}

RootCause KvcacheConnFault002_005::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string KvcacheConnFault002_005::GetFixSuggDesc() const
{
    return "业务方自查Put/Get顺序、key正确性、TTL设置（08手册:L251）。";
}

std::string KvcacheConnFault002_005::GetValidationMethodDesc() const
{
    return "通过日志关键字识别（08手册:L251）：匹配Can't find object或K_NOT_FOUND；"
           "注意K_NOT_FOUND在access log会被记成code=0（08手册:L22）。";
}

std::string KvcacheConnFault002_005::GetId() const
{
    return "kvcache_conn_fault_002_005";
}
} // namespace diag
