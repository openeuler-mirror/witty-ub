#include "kvcache_conn_fault_002_004.h"

#include "../../failure_mode_factory.h"

namespace diag {

static AutoRegister<KvcacheConnFault002_004> g_kvcacheconnfault("kvcache_conn_fault_002_004");

bool KvcacheConnFault002_004::IsValid(const std::vector<std::string> &fields)
{
    if (fields.size() <= 7) {
        return false;
    }
    const std::string &message = fields[7];
    return (message.find("OBJECT_KEYS_MAX_SIZE_LIMIT") != std::string::npos);
}

std::string KvcacheConnFault002_004::GetName() const
{
    return "respMsg批次超限故障。";
}

std::string KvcacheConnFault002_004::GetRootCauseDesc() const
{
    return "批处理大小超过最大限制，属于用户侧问题（08手册:L250）。";
}

RootCause KvcacheConnFault002_004::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string KvcacheConnFault002_004::GetFixSuggDesc() const
{
    return "拆分批次，减小单次请求的对象数量（08手册:L250）。";
}

std::string KvcacheConnFault002_004::GetValidationMethodDesc() const
{
    return "通过日志关键字识别（08手册:L250）：匹配OBJECT_KEYS_MAX_SIZE_LIMIT。";
}

std::string KvcacheConnFault002_004::GetId() const
{
    return "kvcache_conn_fault_002_004";
}
} // namespace diag
