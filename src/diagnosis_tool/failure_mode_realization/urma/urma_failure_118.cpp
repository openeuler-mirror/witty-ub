#include "urma_failure_118.h"
#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure118> g_urma("urma_118");

bool UrmaFailure118::IsValid()
{
    std::string grepOutput = urma_log_helper::RunCommand(
        R"(test -n "$URMA_LOG_PATH" && grep -F 'urma_active_jfr' "$URMA_LOG_PATH" 2>/dev/null | grep -F 'Invalid parameter, trans_mode')");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure118::GetName() const
{
    return "urma_active_jfr 校验 JFR 无效导致激活流程拒绝继续执行";
}

std::string UrmaFailure118::GetRootCauseDesc() const
{
    return "urma_active_jfr 在执行激活前发现调用方传入的 JFR 不满足当前操作要求，通常是对象为空、状态不匹配或与 "
           "provider 能力不一致，因此直接返回错误以避免继续访问非法资源。";
}

RootCause UrmaFailure118::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure118::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure118::GetValidationMethodDesc() const
{
    return "在 URMA_LOG_PATH 中匹配关键日志：Invalid parameter, trans_mode";
}

std::string UrmaFailure118::GetId() const
{
    return "urma_118";
}

} // namespace diag
