#include "urma_failure_893.h"
#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure893> g_urma("urma_893");

bool UrmaFailure893::IsValid()
{
    std::string grepOutput = urma_log_helper::RunCommand(
        "test -n \"$URMA_LOG_PATH\" && "
        "grep -F 'urma_check_seg_cfg' \"$URMA_LOG_PATH\" 2>/dev/null | "
        "grep -F 'Write access should be config with read access'");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure893::GetName() const
{
    return "urma_check_seg_cfg 执行校验 segment 失败导致当前资源状态无法推进";
}

std::string UrmaFailure893::GetRootCauseDesc() const
{
    return "urma_check_seg_cfg 调用下层 provider、bond 组件或系统接口处理 segment 时返回失败，当前分支携带 ret/errno "
           "等错误结果退出，导致该资源的创建、导入、修改、投递或清理状态无法继续推进。";
}

RootCause UrmaFailure893::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure893::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure893::GetValidationMethodDesc() const
{
    return "在 URMA_LOG_PATH 中匹配关键日志：Write access should be config with read access";
}

std::string UrmaFailure893::GetId() const
{
    return "urma_893";
}

} // namespace diag
