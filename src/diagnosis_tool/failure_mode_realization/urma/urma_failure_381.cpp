#include "urma_failure_381.h"
#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure381> g_urma("urma_381");

bool UrmaFailure381::IsValid()
{
    std::string grepOutput =
        urma_log_helper::RunCommand("test -n \"$URMA_LOG_PATH\" && grep -F 'urma_cmd_alloc_jfr' \"$URMA_LOG_PATH\" "
                                    "2>/dev/null | grep -F 'Invalid parameter'");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure381::GetName() const
{
    return "URMA context、JFR对象、Jetty对象、目标Jetty对象无效导致分配JFR失败";
}

std::string UrmaFailure381::GetRootCauseDesc() const
{
    return "函数用于分配JFR，调用方传入的URMA "
           "context、JFR对象、Jetty对象、目标Jetty对象不满足接口前置条件，无法继续完成本次URMA操作。";
}

RootCause UrmaFailure381::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure381::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure381::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：urma_cmd_alloc_jfr，Invalid parameter。";
}

std::string UrmaFailure381::GetId() const
{
    return "urma_381";
}

} // namespace diag
