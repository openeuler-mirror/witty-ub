#include "urma_failure_532.h"
#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure532> g_urma("urma_532");

bool UrmaFailure532::IsValid()
{
    std::string grepOutput =
        urma_log_helper::RunCommand("test -n \"$URMA_LOG_PATH\" && grep -F 'urma_cmd_unimport_seg' \"$URMA_LOG_PATH\" "
                                    "2>/dev/null | grep -F 'Invalid parameter'");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure532::GetName() const
{
    return "URMA context无效导致解除导入Segment失败";
}

std::string UrmaFailure532::GetRootCauseDesc() const
{
    return "函数用于解除导入Segment，调用方传入的URMA context不满足接口前置条件，无法继续完成本次URMA操作。";
}

RootCause UrmaFailure532::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure532::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure532::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：urma_cmd_unimport_seg，Invalid parameter。";
}

std::string UrmaFailure532::GetId() const
{
    return "urma_532";
}

} // namespace diag
