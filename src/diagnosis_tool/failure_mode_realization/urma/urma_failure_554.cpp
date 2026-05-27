#include "urma_failure_554.h"
#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure554> g_urma("urma_554");

bool UrmaFailure554::IsValid()
{
    std::string grepOutput =
        urma_log_helper::RunCommand("test -n \"$URMA_LOG_PATH\" && grep -F 'post_send_check_valid' \"$URMA_LOG_PATH\" "
                                    "2>/dev/null | grep -F 'Invalid src_chip_id:'");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure554::GetName() const
{
    return "WR对象无效导致投递组件失败";
}

std::string UrmaFailure554::GetRootCauseDesc() const
{
    return "函数用于投递组件，调用方传入的WR对象不满足接口前置条件，无法继续完成本次URMA操作。";
}

RootCause UrmaFailure554::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure554::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure554::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：post_send_check_valid，Invalid src_chip_id:。";
}

std::string UrmaFailure554::GetId() const
{
    return "urma_554";
}

} // namespace diag
