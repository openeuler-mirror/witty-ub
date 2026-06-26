#include "urma_failure_167.h"

#include "../../failure_mode_factory.h"

namespace diag {
static AutoRegister<UrmaFailure167> g_urma("urma_167");

bool UrmaFailure167::IsValid(const std::vector<std::string> &fields)
{
    const std::string &message = fields[7];
    return message.find("create_topo_map") != std::string::npos &&
           message.find("Failed to alloc topo_map") != std::string::npos;
}

std::string UrmaFailure167::GetName() const
{
    return "topo map分配失败导致创建TOPO、MAP失败";
}

std::string UrmaFailure167::GetRootCauseDesc() const
{
    return "create_topo_map执行创建TOPO、MAP前需要准备topo map，内存或资源分配失败会阻断后续URMA操作。";
}

RootCause UrmaFailure167::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure167::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure167::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：create_topo_map，Failed to alloc topo_map。";
}

std::string UrmaFailure167::GetId() const
{
    return "urma_167";
}
} // namespace diag
