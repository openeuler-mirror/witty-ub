#include "urma_failure_285.h"
#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure285> g_urma("urma_285");

bool UrmaFailure285::IsValid()
{
    std::string grepOutput = urma_log_helper::RunCommand(
        R"(test -n "$URMA_LOG_PATH" && grep -F 'create_topo_map' "$URMA_LOG_PATH" 2>/dev/null | grep -F 'Failed to alloc topo_map')");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure285::GetName() const
{
    return "create_topo_map 分配 拓扑信息 临时参数失败导致创建流程无法继续";
}

std::string UrmaFailure285::GetRootCauseDesc() const
{
    return "create_topo_map 需要为 拓扑信息 构造命令参数、资源描述或临时缓存，但内存分配返回失败，后续 provider "
           "调用或驱动命令缺少必要入参，因此当前 URMA 操作被阻断。";
}

RootCause UrmaFailure285::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure285::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure285::GetValidationMethodDesc() const
{
    return "在 URMA_LOG_PATH 中匹配关键日志：Failed to alloc topo_map";
}

std::string UrmaFailure285::GetId() const
{
    return "urma_285";
}

} // namespace diag
