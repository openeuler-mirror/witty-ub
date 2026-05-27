#include "urma_failure_269.h"
#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure269> g_urma("urma_269");

bool UrmaFailure269::IsValid()
{
    std::string grepOutput =
        urma_log_helper::RunCommand("test -n \"$URMA_LOG_PATH\" && grep -F 'urma_set_jetty_opt' \"$URMA_LOG_PATH\" "
                                    "2>/dev/null | grep -F 'Failed to exec urma_jetty_set_options.'");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure269::GetName() const
{
    return "设置Jetty过程中依赖步骤失败";
}

std::string UrmaFailure269::GetRootCauseDesc() const
{
    return "函数用于设置Jetty，执行过程中依赖的参数校验、状态转换、下层provider调用或系统资源处理未成功，导致本次URMA操"
           "作失败。";
}

RootCause UrmaFailure269::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure269::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure269::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：urma_set_jetty_opt，Failed to exec urma_jetty_set_options.。";
}

std::string UrmaFailure269::GetId() const
{
    return "urma_269";
}

} // namespace diag
