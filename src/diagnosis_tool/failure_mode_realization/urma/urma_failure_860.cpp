#include "urma_failure_860.h"
#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure860> g_urma("urma_860");

bool UrmaFailure860::IsValid()
{
    std::string grepOutput =
        urma_log_helper::RunCommand("test -n \"$URMA_LOG_PATH\" && grep -F 'check_valid_sgl' \"$URMA_LOG_PATH\" "
                                    "2>/dev/null | grep -F 'sge is a null pointer.'");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure860::GetName() const
{
    return "执行context过程中依赖步骤失败";
}

std::string UrmaFailure860::GetRootCauseDesc() const
{
    return "函数用于执行context，执行过程中依赖的参数校验、状态转换、下层provider调用或系统资源处理未成功，导致本次URMA"
           "操作失败。";
}

RootCause UrmaFailure860::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure860::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure860::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：check_valid_sgl，sge is a null pointer.。";
}

std::string UrmaFailure860::GetId() const
{
    return "urma_860";
}

} // namespace diag
