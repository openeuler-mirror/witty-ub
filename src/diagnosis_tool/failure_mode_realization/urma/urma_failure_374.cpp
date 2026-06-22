#include "urma_failure_374.h"

#include "../../failure_mode_factory.h"

namespace diag {
static AutoRegister<UrmaFailure374> g_urma("urma_374");

bool UrmaFailure374::IsValid(const std::vector<std::string> &fields)
{
    const std::string &message = fields[7];
    return message.find("comp_post_send") != std::string::npos &&
           message.find("Invalid post jfs wr type:") != std::string::npos;
}

std::string UrmaFailure374::GetName() const
{
    return "COMP状态不满足要求导致投递COMP失败";
}

std::string UrmaFailure374::GetRootCauseDesc() const
{
    return "comp_post_send执行投递COMP时检测到依赖对象、资源状态或返回值异常，因此中止当前URMA操作。";
}

RootCause UrmaFailure374::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure374::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure374::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：comp_post_send，Invalid post jfs wr type:。";
}

std::string UrmaFailure374::GetId() const
{
    return "urma_374";
}
} // namespace diag
