#include "urma_failure_042.h"
#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure042> g_urma("urma_042");

bool UrmaFailure042::IsValid()
{
    std::string grepOutput = urma_log_helper::RunCommand("test -n \"$URMA_LOG_PATH\" && grep -F 'urma_open_provider' "
                                                         "\"$URMA_LOG_PATH\" 2>/dev/null | grep -F 'realpath failed.'");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure042::GetName() const
{
    return "打开URMA资源过程中依赖步骤失败";
}

std::string UrmaFailure042::GetRootCauseDesc() const
{
    return "函数用于打开URMA资源，执行过程中依赖的参数校验、状态转换、下层provider调用或系统资源处理未成功，导致本次URM"
           "A操作失败。";
}

RootCause UrmaFailure042::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure042::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure042::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：urma_open_provider，realpath failed.。";
}

std::string UrmaFailure042::GetId() const
{
    return "urma_042";
}

} // namespace diag
