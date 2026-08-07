#include "kvcache_conn_fault_001.h"

#include "../../failure_mode_factory.h"

namespace diag {

static AutoRegister<KvcacheConnFault001> g_kvcacheconnfault("kvcache_conn_fault_001");

bool KvcacheConnFault001::IsValid(const std::vector<std::string> &fields)
{
    // 来源：kvcache_conn_fault_mode.md:L58-83
    // KVCache中断异常根节点：access log中status_code（第8列，即code）非0即判定
    // 注意：K_NOT_FOUND在access log会被记成code=0，需同时看respMsg是否含NOT_FOUND
    if (fields.size() <= 7) {
        return false;
    }
    int statusCode = std::stoi(fields[7]);
    // 任何非0状态码都匹配；此外code=0但respMsg非空（如NOT_FOUND场景）也匹配
    // 来源：08手册:L74 "code非0大量增多，或进程挂、连接断"
    if (statusCode != 0) {
        return true;
    }
    // 来源：08手册:L22 "K_NOT_FOUND在access log会被记成code=0"
    if (fields.size() > 12 && !fields[12].empty()) {
        return true;
    }
    return false;
}

std::string KvcacheConnFault001::GetName() const
{
    return "KVCache中断异常。";
}

std::string KvcacheConnFault001::GetRootCauseDesc() const
{
    return "向下级匹配。";
}

RootCause KvcacheConnFault001::AnalyzeRootCause()
{
    return RootCause(false, GetRootCauseDesc());
}

std::string KvcacheConnFault001::GetFixSuggDesc() const
{
    return "向下级匹配。";
}

std::string KvcacheConnFault001::GetValidationMethodDesc() const
{
    return "通过接口日志识别（08手册:L14-17）：access log中status_code非0大量增多，"
           "或进程挂、连接断；注意K_NOT_FOUND在access log会被记成code=0"
           "（08手册:L22）。";
}

std::string KvcacheConnFault001::GetId() const
{
    return "kvcache_conn_fault_001";
}
} // namespace diag
