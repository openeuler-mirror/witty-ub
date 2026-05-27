#include "urma_failure_400.h"
#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure400> g_urma("urma_400");

bool UrmaFailure400::IsValid()
{
    std::string grepOutput = urma_log_helper::RunCommand(
        "test -n \"$URMA_LOG_PATH\" && grep -F 'urma_check_ctrlplane_compat' \"$URMA_LOG_PATH\" 2>/dev/null | grep -F "
        "'Token value must be set when token policy is not URMA_TOKEN_NONE.'");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure400::GetName() const
{
    return "设置Token过程中依赖步骤失败";
}

std::string UrmaFailure400::GetRootCauseDesc() const
{
    return "函数用于设置Token，执行过程中依赖的参数校验、状态转换、下层provider调用或系统资源处理未成功，导致本次URMA操"
           "作失败。";
}

RootCause UrmaFailure400::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure400::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure400::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：urma_check_ctrlplane_compat，Token value must be set when token policy "
           "is not URMA_TOKEN_NONE.。";
}

std::string UrmaFailure400::GetId() const
{
    return "urma_400";
}

} // namespace diag
