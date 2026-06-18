#include "urma_failure_611.h"

#include "../../failure_mode_factory.h"

namespace diag {
static AutoRegister<UrmaFailure611> g_urma("urma_611");

bool UrmaFailure611::IsValid(const std::vector<std::string> &fields)
{
    const std::string &message = fields[7];
    return message.find("urma_cmd_query_jfs") != std::string::npos &&
           message.find("Invalid parameter") != std::string::npos;
}

std::string UrmaFailure611::GetName() const
{
    return "ret无效导致查询JFS失败";
}

std::string UrmaFailure611::GetRootCauseDesc() const
{
    return "urma_cmd_query_jfs用于查询JFS，调用方传入的ret不满足接口前置条件，函数无法继续执行。";
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
    return "通过 URMA_LOG_PATH 日志匹配关键字：urma_cmd_query_jfs，Invalid parameter。";
}

std::string UrmaFailure611::GetId() const
{
    return "urma_611";
}
} // namespace diag
