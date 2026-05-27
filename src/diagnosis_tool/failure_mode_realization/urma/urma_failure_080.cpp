#include "urma_failure_080.h"
#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure080> g_urma("urma_080");

bool UrmaFailure080::IsValid()
{
    std::string grepOutput =
        urma_log_helper::RunCommand("test -n \"$URMA_LOG_PATH\" && grep -F 'bondp_delete_jetty' \"$URMA_LOG_PATH\" "
                                    "2>/dev/null | grep -F 'Failed to delete pjetty'");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure080::GetName() const
{
    return "物理 Jetty清理阶段下层释放操作失败";
}

std::string UrmaFailure080::GetRootCauseDesc() const
{
    return "函数负责释放或撤销物理 Jetty相关资源，下层provider、驱动或引用状态返回失败，可能残留已创建的URMA资源。";
}

RootCause UrmaFailure080::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure080::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure080::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：bondp_delete_jetty，Failed to delete pjetty。";
}

std::string UrmaFailure080::GetId() const
{
    return "urma_080";
}

} // namespace diag
