#include "urma_failure_166.h"

#include "../../failure_mode_factory.h"

namespace diag {
static AutoRegister<UrmaFailure166> g_urma("urma_166");

bool UrmaFailure166::IsValid(const std::vector<std::string> &fields)
{
    const std::string &message = fields[7];
    return message.find("create_topo_map") != std::string::npos &&
           message.find("Invalid topo info to create topo map") != std::string::npos;
}

std::string UrmaFailure166::GetName() const
{
    return "TOPO、MAP状态不满足要求导致创建TOPO、MAP失败";
}

std::string UrmaFailure166::GetRootCauseDesc() const
{
    return "create_topo_map执行创建TOPO、MAP时检测到依赖对象、资源状态或返回值异常，因此中止当前URMA操作。";
}

RootCause UrmaFailure166::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure166::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure166::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：create_topo_map，Invalid topo info to create topo map。";
}

std::string UrmaFailure166::GetId() const
{
    return "urma_166";
}
} // namespace diag
