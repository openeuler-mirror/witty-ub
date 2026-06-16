#include "urma_failure_772.h"
#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure772> g_urma("urma_772");

bool UrmaFailure772::IsValid()
{
    std::string grepOutput =
        urma_log_helper::RunCommand("test -n \"$URMA_LOG_PATH\" && grep -F 'urma_modify_jfc' \"$URMA_LOG_PATH\" "
                                    "2>/dev/null | grep -F 'Invalid parameter.'");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure772::GetName() const
{
    return "URMA context、设备对象无效导致修改JFC失败";
}

std::string UrmaFailure772::GetRootCauseDesc() const
{
    return "函数用于修改JFC，调用方传入的URMA context、设备对象不满足接口前置条件，无法继续完成本次URMA操作。";
}

RootCause UrmaFailure772::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure772::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure772::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：urma_modify_jfc，Invalid parameter.。";
}

std::string UrmaFailure772::GetId() const
{
    return "urma_772";
}

} // namespace diag
