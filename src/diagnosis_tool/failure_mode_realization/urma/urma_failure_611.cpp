#include "urma_failure_611.h"
#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure611> g_urma("urma_611");

bool UrmaFailure611::IsValid()
{
    std::string grepOutput =
        urma_log_helper::RunCommand("test -n \"$URMA_LOG_PATH\" && grep -F 'bondp_delete_pcontext' \"$URMA_LOG_PATH\" "
                                    "2>/dev/null | grep -F 'Failed to delete pctx, idx:' | grep -F ', ret:'");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure611::GetName() const
{
    return "设备清理阶段下层释放操作失败";
}

std::string UrmaFailure611::GetRootCauseDesc() const
{
    return "函数负责释放或撤销设备相关资源，下层provider、驱动或引用状态返回失败，可能残留已创建的URMA资源。";
}

RootCause UrmaFailure611::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure611::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure611::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：bondp_delete_pcontext，Failed to delete pctx, idx:，, ret:。";
}

std::string UrmaFailure611::GetId() const
{
    return "urma_611";
}

} // namespace diag
