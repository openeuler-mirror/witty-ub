#include "urma_failure_813.h"
#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure813> g_urma("urma_813");

bool UrmaFailure813::IsValid()
{
    std::string grepOutput =
        urma_log_helper::RunCommand("test -n \"$URMA_LOG_PATH\" && grep -F 'urma_modify_jfr' \"$URMA_LOG_PATH\" "
                                    "2>/dev/null | grep -F 'Invalid parameter.'");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure813::GetName() const
{
    return "URMA context、设备对象、JFR对象无效导致修改JFR失败";
}

std::string UrmaFailure813::GetRootCauseDesc() const
{
    return "函数用于修改JFR，调用方传入的URMA context、设备对象、JFR对象不满足接口前置条件，无法继续完成本次URMA操作。";
}

RootCause UrmaFailure813::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure813::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure813::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：urma_modify_jfr，Invalid parameter.。";
}

std::string UrmaFailure813::GetId() const
{
    return "urma_813";
}

} // namespace diag
