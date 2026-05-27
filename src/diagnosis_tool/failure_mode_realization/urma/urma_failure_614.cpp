#include "urma_failure_614.h"
#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure614> g_urma("urma_614");

bool UrmaFailure614::IsValid()
{
    std::string grepOutput =
        urma_log_helper::RunCommand("test -n \"$URMA_LOG_PATH\" && grep -F 'bondp_set_bonding_mode' \"$URMA_LOG_PATH\" "
                                    "2>/dev/null | grep -F 'Failed to delete pctx when set bonding mode, ret:'");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure614::GetName() const
{
    return "锁清理阶段下层释放操作失败";
}

std::string UrmaFailure614::GetRootCauseDesc() const
{
    return "函数负责释放或撤销锁相关资源，下层provider、驱动或引用状态返回失败，可能残留已创建的URMA资源。";
}

RootCause UrmaFailure614::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure614::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure614::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：bondp_set_bonding_mode，Failed to delete pctx when set bonding mode, "
           "ret:。";
}

std::string UrmaFailure614::GetId() const
{
    return "urma_614";
}

} // namespace diag
