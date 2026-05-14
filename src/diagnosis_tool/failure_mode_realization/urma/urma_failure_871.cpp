#include "urma_failure_871.h"
#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure871> g_urma("urma_871");

bool UrmaFailure871::IsValid()
{
    std::string grepOutput = urma_log_helper::RunCommand(
        R"(test -n "$URMA_LOG_PATH" && grep -F 'deepcopy_jfr_wr_inner' "$URMA_LOG_PATH" 2>/dev/null | grep -F 'Invalid jfr wr to deepcopy')");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure871::GetName() const
{
    return "deepcopy_jfr_wr_inner 校验 JFR 无效导致复制流程拒绝继续执行";
}

std::string UrmaFailure871::GetRootCauseDesc() const
{
    return "deepcopy_jfr_wr_inner 在执行复制前发现调用方传入的 JFR 不满足当前操作要求，通常是对象为空、状态不匹配或与 "
           "provider 能力不一致，因此直接返回错误以避免继续访问非法资源。";
}

RootCause UrmaFailure871::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure871::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure871::GetValidationMethodDesc() const
{
    return "在 URMA_LOG_PATH 中匹配关键日志：Invalid jfr wr to deepcopy";
}

std::string UrmaFailure871::GetId() const
{
    return "urma_871";
}

} // namespace diag
