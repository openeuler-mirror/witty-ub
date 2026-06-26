/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2026. All rights reserved.
 * witty-ub is licensed under the Mulan PSL v2.
 * You can use this software according to the terms and conditions of the Mulan PSL v2.
 * You may obtain a copy of Mulan PSL v2 at:
 *     http://license.coscl.org.cn/MulanPSL2
 * THIS SOFTWARE IS PROVIDED ON AN "AS IS" BASIS, WITHOUT WARRANTIES OF ANY KIND, EITHER EXPRESS OR
 * IMPLIED, INCLUDING BUT NOT LIMITED TO NON-INFRINGEMENT, MERCHANTABILITY OR FIT FOR A PARTICULAR
 * PURPOSE.
 * See the Mulan PSL v2 for more details.
 */

#ifndef FAILURE_MODE_FACTORY_H_
#define FAILURE_MODE_FACTORY_H_

#include <functional>
#include <memory>
#include <string>
#include <unordered_map>
#include <vector>
#include "failure_mode.h"

namespace diag {

class FailureModeFactory {
public:
    using Creator = std::function<std::shared_ptr<FailureMode>()>;

    // 获取单例实例
    static FailureModeFactory &Instance() noexcept;

    // 注册故障模式类型
    void Register(const std::string &typeId, Creator creator) noexcept;

    // 创建故障模式实例
    std::shared_ptr<FailureMode> Create(const std::string &typeId) const noexcept;

    // 获取所有已注册的类型ID
    std::vector<std::string> GetAllTypeIds() const noexcept;

    // 检查是否已注册
    bool IsRegistered(const std::string &typeId) const noexcept;

private:
    FailureModeFactory() = default;
    std::unordered_map<std::string, Creator> m_creators;
};

// 自动注册辅助类模板，FailureMode派生类定义时必须构造该类
template <typename T>
class AutoRegister {
public:
    explicit AutoRegister(const std::string &typeId) noexcept
    {
        try {
            FailureModeFactory::Instance().Register(typeId, &AutoRegister::Create);
        } catch (...) {
            std::terminate();
        }
    }

private:
    static std::shared_ptr<FailureMode> Create() noexcept
    {
        try {
            return std::make_shared<T>();
        } catch (...) {
            return nullptr;
        }
    }
};
} // namespace diag

#endif // FAILURE_MODE_FACTORY_H_