#include "urma_failure_488.h"

#include "../../failure_mode_factory.h"

namespace diag {
static AutoRegister<UrmaFailure488> g_urma("urma_488");

bool UrmaFailure488::IsValid(const std::vector<std::string> &fields)
{
    const std::string &message = fields[7];
    return message.find("urma_recv") != std::string::npos && message.find("Invalid parameter.") != std::string::npos;
}

std::string UrmaFailure488::GetName() const
{
    return "dp_ops、post_jfr_wr、recv_tseg无效导致接收URMA资源失败";
}

std::string UrmaFailure488::GetRootCauseDesc() const
{
    return "urma_recv用于接收URMA资源，调用方传入的dp_ops、post_jfr_wr、recv_"
           "tseg不满足接口前置条件，函数无法继续执行。";
}

RootCause UrmaFailure488::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure488::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure488::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：urma_recv，Invalid parameter.。";
}

std::string UrmaFailure488::GetId() const
{
    return "urma_488";
}
} // namespace diag
