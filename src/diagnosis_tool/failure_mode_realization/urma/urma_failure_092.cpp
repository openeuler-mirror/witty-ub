#include "urma_failure_092.h"
#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure092> g_urma("urma_092");

bool UrmaFailure092::IsValid()
{
    std::string grepOutput =
        urma_log_helper::RunCommand("test -n \"$URMA_LOG_PATH\" && grep -F 'bondp_unimport_pjfr' \"$URMA_LOG_PATH\" "
                                    "2>/dev/null | grep -F 'Failed to alloc target jetty'");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure092::GetName() const
{
    return "Jetty相关临时结构或命令参数分配失败";
}

std::string UrmaFailure092::GetRootCauseDesc() const
{
    return "函数在分配Jetty前需要申请命令参数、资源描述或临时缓存，内存分配失败会阻断后续URMA资源处理。";
}

RootCause UrmaFailure092::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure092::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure092::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：bondp_unimport_pjfr，Failed to alloc target jetty。";
}

std::string UrmaFailure092::GetId() const
{
    return "urma_092";
}

} // namespace diag
