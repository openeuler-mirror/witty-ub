#include "urma_failure_261.h"
#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure261> g_urma("urma_261");

bool UrmaFailure261::IsValid()
{
    std::string grepOutput =
        urma_log_helper::RunCommand("test -n \"$URMA_LOG_PATH\" && grep -F 'urma_alloc_jetty' \"$URMA_LOG_PATH\" "
                                    "2>/dev/null | grep -F 'Invalid parameter.'");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure261::GetName() const
{
    return "URMA context、provider操作表无效导致分配Jetty失败";
}

std::string UrmaFailure261::GetRootCauseDesc() const
{
    return "函数用于分配Jetty，调用方传入的URMA context、provider操作表不满足接口前置条件，无法继续完成本次URMA操作。";
}

RootCause UrmaFailure261::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure261::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure261::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：urma_alloc_jetty，Invalid parameter.。";
}

std::string UrmaFailure261::GetId() const
{
    return "urma_261";
}

} // namespace diag
