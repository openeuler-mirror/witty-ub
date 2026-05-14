#include "urma_failure_302.h"
#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure302> g_urma("urma_302");

bool UrmaFailure302::IsValid()
{
    std::string grepOutput = urma_log_helper::RunCommand(
        R"(test -n "$URMA_LOG_PATH" && grep -F 'deepcopy_jfr_wr_node' "$URMA_LOG_PATH" 2>/dev/null | grep -F 'Malloc wr failed')");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure302::GetName() const
{
    return "deepcopy_jfr_wr_node 分配 JFR 临时参数失败导致复制流程无法继续";
}

std::string UrmaFailure302::GetRootCauseDesc() const
{
    return "deepcopy_jfr_wr_node 需要为 JFR 构造命令参数、资源描述或临时缓存，但内存分配返回失败，后续 provider "
           "调用或驱动命令缺少必要入参，因此当前 URMA 操作被阻断。";
}

RootCause UrmaFailure302::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure302::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure302::GetValidationMethodDesc() const
{
    return "在 URMA_LOG_PATH 中匹配关键日志：Malloc wr failed";
}

std::string UrmaFailure302::GetId() const
{
    return "urma_302";
}

} // namespace diag
