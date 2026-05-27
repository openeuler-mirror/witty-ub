#include "urma_failure_402.h"
#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure402> g_urma("urma_402");

bool UrmaFailure402::IsValid()
{
    std::string grepOutput =
        urma_log_helper::RunCommand("test -n \"$URMA_LOG_PATH\" && grep -F 'urma_alloc_jfr' \"$URMA_LOG_PATH\" "
                                    "2>/dev/null | grep -F 'Invalid parameter, trans_mode:'");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure402::GetName() const
{
    return "URMA context、provider操作表、JFR对象无效导致分配JFR失败";
}

std::string UrmaFailure402::GetRootCauseDesc() const
{
    return "函数用于分配JFR，调用方传入的URMA "
           "context、provider操作表、JFR对象不满足接口前置条件，无法继续完成本次URMA操作。";
}

RootCause UrmaFailure402::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure402::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure402::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：urma_alloc_jfr，Invalid parameter, trans_mode:。";
}

std::string UrmaFailure402::GetId() const
{
    return "urma_402";
}

} // namespace diag
