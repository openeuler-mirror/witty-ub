#include "urma_failure_212.h"
#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure212> g_urma("urma_212");

bool UrmaFailure212::IsValid()
{
    std::string grepOutput = urma_log_helper::RunCommand(
        R"(test -n "$URMA_LOG_PATH" && grep -F 'bondp_jfr_get_args_list' "$URMA_LOG_PATH" 2>/dev/null | grep -F 'Failed to alloc args')");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure212::GetName() const
{
    return "bondp_jfr_get_args_list 分配 JFR 临时参数失败导致获取流程无法继续";
}

std::string UrmaFailure212::GetRootCauseDesc() const
{
    return "bondp_jfr_get_args_list 需要为 JFR 构造命令参数、资源描述或临时缓存，但内存分配返回失败，后续 provider "
           "调用或驱动命令缺少必要入参，因此当前 URMA 操作被阻断。";
}

RootCause UrmaFailure212::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure212::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure212::GetValidationMethodDesc() const
{
    return "在 URMA_LOG_PATH 中匹配关键日志：Failed to alloc args";
}

std::string UrmaFailure212::GetId() const
{
    return "urma_212";
}

} // namespace diag
