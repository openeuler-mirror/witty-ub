#include "urma_failure_107.h"

#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure107> g_urma("urma_107");

bool UrmaFailure107::IsValid()
{
    std::string grepOutput = urma_log_helper::RunCommand(
        "test -n \"$URMA_LOG_PATH\" && grep -F 'bondp_relink_primary_import' \"$URMA_LOG_PATH\" 2>/dev/null | "
        "grep -F 'Failed to import recreated primary ptjetty, local_idx:' | grep -F 'target_idx:' | grep -F "
        "'pjetty_id:'");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure107::GetName() const
{
    return "物理 Jetty导入时下层资源准备失败";
}

std::string UrmaFailure107::GetRootCauseDesc() const
{
    return "函数负责导入物理 Jetty，依赖的provider接口、驱动命令、子资源或路由信息未成功返回，导致资源无法建立。";
}

RootCause UrmaFailure107::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure107::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure107::GetValidationMethodDesc() const
{
    return "通过 URMA 日志关键字校验：bondp_relink_primary_import，Failed to import recreated primary ptjetty, "
           "local_idx:，target_idx:，pjetty_id:";
}

std::string UrmaFailure107::GetId() const
{
    return "urma_107";
}

} // namespace diag
