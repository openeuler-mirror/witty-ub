#include "urma_failure_459.h"
#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure459> g_urma("urma_459");

bool UrmaFailure459::IsValid()
{
    std::string grepOutput =
        urma_log_helper::RunCommand("test -n \"$URMA_LOG_PATH\" && grep -F 'urma_query_jfr' \"$URMA_LOG_PATH\" "
                                    "2>/dev/null | grep -F 'Invalid parameter.'");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure459::GetName() const
{
    return "URMA context、provider操作表、JFR对象、provider未提供query_jfr操作实现无效导致查询JFR失败";
}

std::string UrmaFailure459::GetRootCauseDesc() const
{
    return "函数用于查询JFR，调用方传入的URMA "
           "context、provider操作表、JFR对象、provider未提供query_"
           "jfr操作实现不满足接口前置条件，无法继续完成本次URMA操作。";
}

RootCause UrmaFailure459::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure459::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure459::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：urma_query_jfr，Invalid parameter.。";
}

std::string UrmaFailure459::GetId() const
{
    return "urma_459";
}

} // namespace diag
