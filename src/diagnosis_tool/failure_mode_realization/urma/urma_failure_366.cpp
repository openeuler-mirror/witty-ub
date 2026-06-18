#include "urma_failure_366.h"

#include "../../failure_mode_factory.h"

namespace diag {
static AutoRegister<UrmaFailure366> g_urma("urma_366");

bool UrmaFailure366::IsValid(const std::vector<std::string> &fields)
{
    const std::string &message = fields[7];
    return message.find("bondp_modify_jfc") != std::string::npos &&
           message.find("modify pjfc fail, index:") != std::string::npos && message.find(", ret:") != std::string::npos;
}

std::string UrmaFailure366::GetName() const
{
    return "修改JFC执行失败导致修改JFC失败";
}

std::string UrmaFailure366::GetRootCauseDesc() const
{
    return "bondp_modify_jfc执行修改JFC时依赖的修改JFC步骤返回错误，当前URMA操作无法继续完成。";
}

RootCause UrmaFailure366::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure366::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure366::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：bondp_modify_jfc，modify pjfc fail, index:，, ret:。";
}

std::string UrmaFailure366::GetId() const
{
    return "urma_366";
}
} // namespace diag
