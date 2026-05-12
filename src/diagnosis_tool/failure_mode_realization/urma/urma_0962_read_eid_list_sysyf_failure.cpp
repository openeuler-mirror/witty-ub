#include "urma_0962_read_eid_list_sysyf_failure.h"
#include <vector>
#include "../../failure_mode_factory.h"
#include "urma_log_matcher.h"

namespace diag {

static AutoRegister<Urma0962ReadEidListSysyfFailure> g_urma("urma_0962");

bool Urma0962ReadEidListSysyfFailure::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> patterns = {"printf failed, eid idx: %."};
    return MatchUrmaLogLine(patterns, logContent);
}

std::string Urma0962ReadEidListSysyfFailure::GetName() const
{
    return "read_eid_list_sysyf 格式化输出失败";
}

std::string Urma0962ReadEidListSysyfFailure::GetRootCauseDesc() const
{
    return "路径或字符串处理失败，可能由于缓冲区长度不足、输入名称异常或系统调用返回错误";
}

RootCause Urma0962ReadEidListSysyfFailure::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string Urma0962ReadEidListSysyfFailure::GetFixSuggDesc() const
{
    return "无";
}

std::string Urma0962ReadEidListSysyfFailure::GetValidationMethodDesc() const
{
    return "在 URMA_LOG_PATH 指定日志中匹配关键日志：printf failed, eid idx: %.";
}

std::string Urma0962ReadEidListSysyfFailure::GetId() const
{
    return "urma_0962";
}
} // namespace diag
