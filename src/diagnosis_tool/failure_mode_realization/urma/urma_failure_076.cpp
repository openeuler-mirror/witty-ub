#include "urma_failure_076.h"

#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure076> g_urma("urma_076");

bool UrmaFailure076::IsValid()
{
    std::string grepOutput = urma_log_helper::RunCommand(
        "test -n \"$URMA_LOG_PATH\" && grep -F 'bondp_delete_jetty' \"$URMA_LOG_PATH\" 2>/dev/null | "
        "grep -F 'Failed to delete jetty[' | grep -F '], still in use. use_cnt:' | grep -F 'u'");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure076::GetName() const
{
    return "Jetty清理阶段下层释放操作失败";
}

std::string UrmaFailure076::GetRootCauseDesc() const
{
    return "函数负责释放或撤销Jetty相关资源，下层provider、驱动或引用状态返回失败，可能残留已创建的URMA资源。";
}

RootCause UrmaFailure076::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure076::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure076::GetValidationMethodDesc() const
{
    return "通过 URMA 日志关键字校验：bondp_delete_jetty，Failed to delete jetty[，], still in use. use_cnt:，u";
}

std::string UrmaFailure076::GetId() const
{
    return "urma_076";
}

} // namespace diag
