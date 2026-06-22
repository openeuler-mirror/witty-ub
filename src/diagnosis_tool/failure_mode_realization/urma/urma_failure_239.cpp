#include "urma_failure_239.h"

#include "../../failure_mode_factory.h"

namespace diag {
static AutoRegister<UrmaFailure239> g_urma("urma_239");

bool UrmaFailure239::IsValid(const std::vector<std::string> &fields)
{
    const std::string &message = fields[7];
    return message.find("create_topo_map") != std::string::npos &&
           message.find("Failed to create eid_mapping_hash_table") != std::string::npos;
}

std::string UrmaFailure239::GetName() const
{
    return "下层资源创建失败导致创建TOPO、MAP失败";
}

std::string UrmaFailure239::GetRootCauseDesc() const
{
    return "create_topo_map在创建TOPO、MAP过程中依赖下层对象或provider创建结果，下层返回失败后当前资源无法建立。";
}

RootCause UrmaFailure239::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure239::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure239::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：create_topo_map，Failed to create eid_mapping_hash_table。";
}

std::string UrmaFailure239::GetId() const
{
    return "urma_239";
}
} // namespace diag
