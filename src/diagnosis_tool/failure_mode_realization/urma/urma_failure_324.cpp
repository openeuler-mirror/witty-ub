#include "urma_failure_324.h"
#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure324> g_urma("urma_324");

bool UrmaFailure324::IsValid()
{
    std::string grepOutput = urma_log_helper::RunCommand(
        R"(test -n "$URMA_LOG_PATH" && grep -F 'urma_cmd_delete_jfr_batch' "$URMA_LOG_PATH" 2>/dev/null | grep -F 'Failed to malloc buffer')");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure324::GetName() const
{
    return "urma_cmd_delete_jfr_batch 分配 JFR 临时参数失败导致删除流程无法继续";
}

std::string UrmaFailure324::GetRootCauseDesc() const
{
    return "urma_cmd_delete_jfr_batch 需要为 JFR 构造命令参数、资源描述或临时缓存，但内存分配返回失败，后续 provider "
           "调用或驱动命令缺少必要入参，因此当前 URMA 操作被阻断。";
}

RootCause UrmaFailure324::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure324::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure324::GetValidationMethodDesc() const
{
    return "在 URMA_LOG_PATH 中匹配关键日志：Failed to malloc buffer";
}

std::string UrmaFailure324::GetId() const
{
    return "urma_324";
}

} // namespace diag
