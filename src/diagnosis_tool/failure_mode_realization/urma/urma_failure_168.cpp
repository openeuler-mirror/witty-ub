#include "urma_failure_168.h"

#include "../../failure_mode_factory.h"

namespace diag {
static AutoRegister<UrmaFailure168> g_urma("urma_168");

bool UrmaFailure168::IsValid(const std::vector<std::string> &fields)
{
    const std::string &message = fields[7];
    return message.find("create_topo_map") != std::string::npos &&
           message.find("topo info doesn't have cur_node") != std::string::npos;
}

std::string UrmaFailure168::GetName() const
{
    return "TOPO、MAP状态不满足要求导致创建TOPO、MAP失败";
}

std::string UrmaFailure168::GetRootCauseDesc() const
{
    return "create_topo_map执行创建TOPO、MAP时检测到依赖对象、资源状态或返回值异常，因此中止当前URMA操作。";
}

RootCause UrmaFailure168::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure168::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure168::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：create_topo_map，topo info doesn't have cur_node。";
}

std::string UrmaFailure168::GetId() const
{
    return "urma_168";
}
} // namespace diag
