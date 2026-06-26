#include "urma_failure_574.h"

#include "../../failure_mode_factory.h"

namespace diag {
static AutoRegister<UrmaFailure574> g_urma("urma_574");

bool UrmaFailure574::IsValid(const std::vector<std::string> &fields)
{
    const std::string &message = fields[7];
    return message.find("urma_free_jfr") != std::string::npos &&
           message.find("Failed to free jfr.") != std::string::npos;
}

std::string UrmaFailure574::GetName() const
{
    return "释放JFR执行失败导致释放JFR失败";
}

std::string UrmaFailure574::GetRootCauseDesc() const
{
    return "urma_free_jfr执行释放JFR时依赖的释放JFR步骤返回错误，当前URMA操作无法继续完成。";
}

RootCause UrmaFailure574::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure574::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure574::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：urma_free_jfr，Failed to free jfr.。";
}

std::string UrmaFailure574::GetId() const
{
    return "urma_574";
}
} // namespace diag
