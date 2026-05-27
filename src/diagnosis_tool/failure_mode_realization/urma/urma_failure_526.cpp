#include "urma_failure_526.h"

#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure526> g_urma("urma_526");

bool UrmaFailure526::IsValid()
{
    std::string grepOutput = urma_log_helper::RunCommand(
        "test -n \"$URMA_LOG_PATH\" && grep -F 'urma_cmd_import_seg' \"$URMA_LOG_PATH\" 2>/dev/null | "
        "grep -F 'Invalid parameter'");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure526::GetName() const
{
    return "URMA context、Segment对象无效导致导入Segment失败";
}

std::string UrmaFailure526::GetRootCauseDesc() const
{
    return "函数用于导入Segment，调用方传入的URMA context、Segment对象不满足接口前置条件，无法继续完成本次URMA操作。";
}

RootCause UrmaFailure526::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure526::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure526::GetValidationMethodDesc() const
{
    return "通过 URMA 日志关键字校验：urma_cmd_import_seg，Invalid parameter";
}

std::string UrmaFailure526::GetId() const
{
    return "urma_526";
}

} // namespace diag
