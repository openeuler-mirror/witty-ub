#include "urma_failure_516.h"
#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure516> g_urma("urma_516");

bool UrmaFailure516::IsValid()
{
    std::string grepOutput =
        urma_log_helper::RunCommand("test -n \"$URMA_LOG_PATH\" && grep -F 'bondp_create_vseg' \"$URMA_LOG_PATH\" "
                                    "2>/dev/null | grep -F 'Invalid token id for register bondp seg'");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure516::GetName() const
{
    return "URMA context、Segment对象无效导致注册Token失败";
}

std::string UrmaFailure516::GetRootCauseDesc() const
{
    return "函数用于注册Token，调用方传入的URMA context、Segment对象不满足接口前置条件，无法继续完成本次URMA操作。";
}

RootCause UrmaFailure516::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure516::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure516::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：bondp_create_vseg，Invalid token id for register bondp seg。";
}

std::string UrmaFailure516::GetId() const
{
    return "urma_516";
}

} // namespace diag
