#include "urma_failure_490.h"

#include "../../failure_mode_factory.h"

namespace diag {
static AutoRegister<UrmaFailure490> g_urma("urma_490");

bool UrmaFailure490::IsValid(const std::vector<std::string> &fields)
{
    const std::string &message = fields[7];
    return message.find("urma_poll_jfc") != std::string::npos &&
           message.find("Invalid parameter.") != std::string::npos;
}

std::string UrmaFailure490::GetName() const
{
    return "dp_ops、poll_jfc、cr、cr_cnt无效导致轮询JFC失败";
}

std::string UrmaFailure490::GetRootCauseDesc() const
{
    return "urma_poll_jfc用于轮询JFC，调用方传入的dp_ops、poll_jfc、cr、cr_cnt不满足接口前置条件，函数无法继续执行。";
}

RootCause UrmaFailure490::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure490::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure490::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：urma_poll_jfc，Invalid parameter.。";
}

std::string UrmaFailure490::GetId() const
{
    return "urma_490";
}
} // namespace diag
