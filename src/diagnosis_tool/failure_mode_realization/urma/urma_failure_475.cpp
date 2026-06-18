#include "urma_failure_475.h"

#include "../../failure_mode_factory.h"

namespace diag {
static AutoRegister<UrmaFailure475> g_urma("urma_475");

bool UrmaFailure475::IsValid(const std::vector<std::string> &fields)
{
    const std::string &message = fields[7];
    return message.find("urma_active_jfr") != std::string::npos &&
           message.find("jfr or jfc state is wrong in active_jfr.") != std::string::npos;
}

std::string UrmaFailure475::GetName() const
{
    return "JFR状态不满足要求导致激活JFR失败";
}

std::string UrmaFailure475::GetRootCauseDesc() const
{
    return "urma_active_jfr执行激活JFR时检测到依赖对象、资源状态或返回值异常，因此中止当前URMA操作。";
}

RootCause UrmaFailure475::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure475::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure475::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：urma_active_jfr，jfr or jfc state is wrong in active_jfr.。";
}

std::string UrmaFailure475::GetId() const
{
    return "urma_475";
}
} // namespace diag
