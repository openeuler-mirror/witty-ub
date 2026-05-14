#include "urma_failure_284.h"
#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure284> g_urma("urma_284");

bool UrmaFailure284::IsValid()
{
    std::string grepOutput = urma_log_helper::RunCommand(
        R"(test -n "$URMA_LOG_PATH" && grep -F 'create_topo_map' "$URMA_LOG_PATH" 2>/dev/null | grep -F 'Invalid topo info to create topo map')");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure284::GetName() const
{
    return "create_topo_map 校验 拓扑信息 无效导致创建流程拒绝继续执行";
}

std::string UrmaFailure284::GetRootCauseDesc() const
{
    return "create_topo_map 在执行创建前发现调用方传入的 拓扑信息 不满足当前操作要求，通常是对象为空、状态不匹配或与 "
           "provider 能力不一致，因此直接返回错误以避免继续访问非法资源。";
}

RootCause UrmaFailure284::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure284::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure284::GetValidationMethodDesc() const
{
    return "在 URMA_LOG_PATH 中匹配关键日志：Invalid topo info to create topo map";
}

std::string UrmaFailure284::GetId() const
{
    return "urma_284";
}

} // namespace diag
