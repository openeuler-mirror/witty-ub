#include "urma_failure_544.h"

#include "../../failure_mode_factory.h"

namespace diag {
static AutoRegister<UrmaFailure544> g_urma("urma_544");

bool UrmaFailure544::IsValid(const std::vector<std::string> &fields)
{
    const std::string &message = fields[7];
    return message.find("urma_cmd_deactive_jfr") != std::string::npos &&
           message.find("Invalid parameter") != std::string::npos;
}

std::string UrmaFailure544::GetName() const
{
    return "JFR、URMA context、dev_fd无效导致去激活JFR失败";
}

std::string UrmaFailure544::GetRootCauseDesc() const
{
    return "urma_cmd_deactive_jfr用于去激活JFR，调用方传入的JFR、URMA "
           "context、dev_fd不满足接口前置条件，函数无法继续执行。";
}

RootCause UrmaFailure544::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure544::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure544::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：urma_cmd_deactive_jfr，Invalid parameter。";
}

std::string UrmaFailure544::GetId() const
{
    return "urma_544";
}
} // namespace diag
