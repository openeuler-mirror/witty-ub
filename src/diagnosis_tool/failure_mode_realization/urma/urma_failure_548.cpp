#include "urma_failure_548.h"
#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure548> g_urma("urma_548");

bool UrmaFailure548::IsValid()
{
    std::string grepOutput =
        urma_log_helper::RunCommand("test -n \"$URMA_LOG_PATH\" && grep -F 'comp_post_send' \"$URMA_LOG_PATH\" "
                                    "2>/dev/null | grep -F 'Invalid post jfs wr type:'");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure548::GetName() const
{
    return "JFS对象、WR对象无效导致投递JFS失败";
}

std::string UrmaFailure548::GetRootCauseDesc() const
{
    return "函数用于投递JFS，调用方传入的JFS对象、WR对象不满足接口前置条件，无法继续完成本次URMA操作。";
}

RootCause UrmaFailure548::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure548::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure548::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：comp_post_send，Invalid post jfs wr type:。";
}

std::string UrmaFailure548::GetId() const
{
    return "urma_548";
}

} // namespace diag
