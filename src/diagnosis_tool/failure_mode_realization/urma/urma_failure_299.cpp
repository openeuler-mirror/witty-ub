#include "urma_failure_299.h"
#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure299> g_urma("urma_299");

bool UrmaFailure299::IsValid()
{
    std::string grepOutput = urma_log_helper::RunCommand(
        "test -n \"$URMA_LOG_PATH\" && "
        "grep -F 'deepcopy_faa_wr' \"$URMA_LOG_PATH\" 2>/dev/null | "
        "grep -F 'Failed to deepcopy src sge'");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure299::GetName() const
{
    return "deepcopy_faa_wr 执行复制 WR 失败导致当前资源状态无法推进";
}

std::string UrmaFailure299::GetRootCauseDesc() const
{
    return "deepcopy_faa_wr 调用下层 provider、bond 组件或系统接口处理 WR 时返回失败，当前分支携带 ret/errno "
           "等错误结果退出，导致该资源的创建、导入、修改、投递或清理状态无法继续推进。";
}

RootCause UrmaFailure299::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure299::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure299::GetValidationMethodDesc() const
{
    return "在 URMA_LOG_PATH 中匹配关键日志：Failed to deepcopy src sge";
}

std::string UrmaFailure299::GetId() const
{
    return "urma_299";
}

} // namespace diag
