#include "urma_failure_531.h"
#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure531> g_urma("urma_531");

bool UrmaFailure531::IsValid()
{
    std::string grepOutput =
        urma_log_helper::RunCommand("test -n \"$URMA_LOG_PATH\" && grep -F 'urma_cmd_import_seg' \"$URMA_LOG_PATH\" "
                                    "2>/dev/null | grep -F 'Invalid parameter'");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure531::GetName() const
{
    return "URMA context、Segment对象无效导致导入Segment失败";
}

std::string UrmaFailure531::GetRootCauseDesc() const
{
    return "函数用于导入Segment，调用方传入的URMA context、Segment对象不满足接口前置条件，无法继续完成本次URMA操作。";
}

RootCause UrmaFailure531::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure531::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure531::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：urma_cmd_import_seg，Invalid parameter。";
}

std::string UrmaFailure531::GetId() const
{
    return "urma_531";
}

} // namespace diag
