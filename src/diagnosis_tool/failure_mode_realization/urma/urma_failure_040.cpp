#include "urma_failure_040.h"
#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure040> g_urma("urma_040");

bool UrmaFailure040::IsValid()
{
    std::string grepOutput =
        urma_log_helper::RunCommand("test -n \"$URMA_LOG_PATH\" && grep -F 'urma_close_provider' \"$URMA_LOG_PATH\" "
                                    "2>/dev/null | grep -F 'close failed, err:'");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure040::GetName() const
{
    return "执行URMA资源过程中依赖步骤失败";
}

std::string UrmaFailure040::GetRootCauseDesc() const
{
    return "函数用于执行URMA资源，执行过程中依赖的参数校验、状态转换、下层provider调用或系统资源处理未成功，导致本次URM"
           "A操作失败。";
}

RootCause UrmaFailure040::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure040::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure040::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：urma_close_provider，close failed, err:。";
}

std::string UrmaFailure040::GetId() const
{
    return "urma_040";
}

} // namespace diag
